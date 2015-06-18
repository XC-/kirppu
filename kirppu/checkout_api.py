from __future__ import unicode_literals, print_function, absolute_import
import inspect

from django.contrib.auth import get_user_model

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.http.response import (
    HttpResponse,
    StreamingHttpResponse,
)
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.utils.six import string_types, text_type, iteritems
from django.utils.translation import ugettext as _
from django.utils.timezone import now

from .models import (
    Item,
    Receipt,
    Clerk,
    Counter,
    ReceiptItem,
    Vendor,
    UserAdapter,
    ItemStateLog,
    Box,
)
from .fields import ItemPriceField
from .forms import ItemRemoveForm

from . import ajax_util
from .ajax_util import (
    AjaxError,
    get_counter,
    get_clerk,
    require_counter_validated,
    require_clerk_login,
    require_overseer_clerk_login,
    RET_BAD_REQUEST,
    RET_CONFLICT,
    RET_AUTH_FAILED,
    RET_LOCKED,
)


def raise_if_item_not_available(item):
    """Raise appropriate AjaxError if item is not in buyable state."""
    if item.state == Item.STAGED:
        # Staged somewhere other?
        raise AjaxError(RET_LOCKED, 'Item is already staged to be sold.')
    elif item.state == Item.ADVERTISED:
        return 'Item has not been brought to event.'
    elif item.state in (Item.SOLD, Item.COMPENSATED):
        raise AjaxError(RET_CONFLICT, 'Item has already been sold.')
    elif item.state == Item.RETURNED:
        raise AjaxError(RET_CONFLICT, 'Item has already been returned to owner.')
    return None


# Registry for ajax functions. Maps function names to AjaxFuncs.
AJAX_FUNCTIONS = {}


def _register_ajax_func(func):
    AJAX_FUNCTIONS[func.name] = func


def ajax_func(url, method='POST', counter=True, clerk=True, overseer=False, atomic=False):
    """
    Decorate a function with some common logic.
    The names of the function being decorated are required to be present in the JSON object
    that is passed to the function, and they are automatically decoded and passed to those
    arguments.

    :param url: URL RegEx this function is served in.
    :type url: str
    :param method: HTTP Method required. Default is POST.
    :type method: str
    :param counter: Is registered Counter required? Default: True.
    :type counter: bool
    :param clerk: Is logged in Clerk required? Default: True.
    :type clerk: bool
    :param overseer: Is overseer permission required for Clerk? Default: False.
    :type overseer: bool
    :param atomic: Should this function run in atomic transaction? Default: False.
    :type atomic: bool
    :return: Decorated function.
    """

    def decorator(func):
        # Get argspec before any decoration.
        (args, _, _, defaults) = inspect.getargspec(func)

        if counter:
            func = require_counter_validated(func)
        if clerk:
            func = require_clerk_login(func)
        if overseer:
            func = require_overseer_clerk_login(func)
        fn = ajax_util.ajax_func(
            url,
            _register_ajax_func,
            method,
            args[1:],
            defaults
        )(func)
        if atomic:
            fn = transaction.atomic(fn)
        return fn
    return decorator


def checkout_js(request):
    """
    Render the JavaScript file that defines the AJAX API functions.
    """
    context = {
        'funcs': iteritems(AJAX_FUNCTIONS),
        'api_name': 'Api',
    }
    return render(
        request,
        "kirppu/app_ajax_api.js",
        context,
        content_type="application/javascript"
    )


def _get_item_or_404(code):
    try:
        item = Item.get_item_by_barcode(code)
    except Item.DoesNotExist:
        item = None

    if item is None:
        raise Http404(_(u"No item found matching '{0}'").format(code))
    return item


@transaction.atomic
def item_mode_change(code, from_, to, message_if_not_first=None):
    item = _get_item_or_404(code)
    if not isinstance(from_, tuple):
        from_ = (from_,)
    if item.state in from_:
        if item.hidden:
            # If an item is brought to the event, even though the user deleted it, it should begin showing again in
            # users list. The same probably applies to any interaction with the item.
            item.hidden = False

        ItemStateLog.objects.log_state(item=item, new_state=to)
        old_state = item.state
        item.state = to
        item.save()
        ret = item.as_dict()
        if message_if_not_first is not None and len(from_) > 1 and old_state != from_[0]:
            ret.update(_message=message_if_not_first)
        return ret

    else:
        # Item not in expected state.
        raise AjaxError(
            RET_CONFLICT,
            _(u"Unexpected item state: {state_name} ({state})").format(
                state=item.state,
                state_name=item.get_state_display()
            ),
        )


@ajax_func('^clerk/login$', clerk=False, counter=False)
def clerk_login(request, code, counter):
    try:
        counter_obj = Counter.objects.get(identifier=counter)
    except Counter.DoesNotExist:
        raise AjaxError(RET_AUTH_FAILED, _(u"Counter has gone missing."))

    try:
        clerk = Clerk.by_code(code)
    except ValueError as ve:
        raise AjaxError(RET_AUTH_FAILED, repr(ve))

    if clerk is None:
        raise AjaxError(RET_AUTH_FAILED, _(u"No such clerk."))

    clerk_data = clerk.as_dict()
    clerk_data['overseer_enabled'] = clerk.user.has_perm('kirppu.oversee')
    clerk_data['stats_enabled'] = clerk.user.is_staff

    active_receipts = Receipt.objects.filter(clerk=clerk, status=Receipt.PENDING)
    if active_receipts:
        if len(active_receipts) > 1:
            clerk_data["receipts"] = [receipt.as_dict() for receipt in active_receipts]
            clerk_data["receipt"] = "MULTIPLE"
        else:
            receipt = active_receipts[0]
            request.session["receipt"] = receipt.pk
            clerk_data["receipt"] = receipt.as_dict()

    request.session["clerk"] = clerk.pk
    request.session["clerk_token"] = clerk.access_key
    request.session["counter"] = counter_obj.pk
    return clerk_data


@ajax_func('^clerk/logout$', clerk=False, counter=False)
def clerk_logout(request):
    """
    Logout currently logged in clerk.
    """
    clerk_logout_fn(request)
    return HttpResponse()


def clerk_logout_fn(request):
    """
    The actual logout procedure that can be used from elsewhere too.

    :param request: Active request, for session access.
    """
    for key in ["clerk", "clerk_token", "counter"]:
        request.session.pop(key, None)


@ajax_func('^counter/validate$', clerk=False, counter=False)
def counter_validate(request, code):
    """
    Validates the counter identifier and returns its exact form, if it is
    valid.
    """
    try:
        counter = Counter.objects.get(identifier__iexact=code)
    except Counter.DoesNotExist:
        raise AjaxError(RET_AUTH_FAILED)

    return {"counter": counter.identifier,
            "name": counter.name}


@ajax_func('^item/find$', method='GET')
def item_find(request, code):
    item = _get_item_or_404(code)
    value = item.as_dict()
    if "available" in request.GET:
        message = raise_if_item_not_available(item)
        if message is not None:
            value.update(_message=message)
    return value


@ajax_func('^item/search$', method='GET', overseer=True)
def item_search(request, query, code, vendor, min_price, max_price, item_type, item_state):

    clauses = []

    types = item_type.split()
    if types:
        clauses.append(Q(itemtype__in=types))

    code = code.strip()
    if code:
        clauses.append(Q(code__contains=code))

    if vendor:
        clauses.append(Q(vendor=vendor))

    states = item_state.split()
    if states:
        clauses.append(Q(state__in=states))

    for part in query.split():
        clauses.append(Q(name__icontains=part))

    try:
        clauses.append(Q(price__gte=float(min_price)))
    except ValueError:
        pass

    try:
        clauses.append(Q(price__lte=float(max_price)))
    except ValueError:
        pass

    results = []

    for item in Item.objects.filter(*clauses).all():
        item_dict = item.as_dict()
        item_dict['vendor'] = item.vendor.as_dict()
        results.append(item_dict)

    return results


@ajax_func('^item/edit$', method='POST', overseer=True, atomic=True)
def item_edit(request, code, price, state):
    try:
        price = ItemPriceField().clean(price)
    except ValidationError as v:
        raise AjaxError(RET_BAD_REQUEST, ' '.join(v.messages))

    if state not in {st for (st, _) in Item.STATE}:
        raise AjaxError(RET_BAD_REQUEST, 'Unknown state: {0}'.format(state))

    item = _get_item_or_404(code)

    if price != item.price:
        price_editable_states = {
            Item.ADVERTISED,
            Item.BROUGHT,
        }
        if (item.state not in price_editable_states and
                state not in price_editable_states):
            raise AjaxError(
                RET_BAD_REQUEST,
                'Cannot change price in state "{0}"'.format(item.get_state_display())
            )

    if item.state != state:
        unsold_states = {
            Item.ADVERTISED,
            Item.BROUGHT,
            Item.MISSING,
            Item.RETURNED,
        }
        if item.state not in unsold_states and item.state != Item.STAGED and state in unsold_states:
            # Need to remove item from receipt.
            receipt_ids = ReceiptItem.objects.filter(
                action=ReceiptItem.ADD,
                item=item,
            ).values_list('receipt_id', flat=True)

            for receipt_id in receipt_ids:
                remove_form = ItemRemoveForm({
                    'receipt': receipt_id,
                    'item': item.code,
                })
                assert remove_form.is_valid()
                remove_form.save()
        else:
            raise AjaxError(
                RET_BAD_REQUEST,
                u'Cannot change state from "{0}" to "{1}".'.format(
                    item.get_state_display(), text_type(dict(Item.STATE)[state])
                )
            )

    item.state = state
    item.price = price
    item.save()

    item_dict = item.as_dict()
    item_dict['vendor'] = item.vendor.as_dict()
    return item_dict


@ajax_func('^item/list$', method='GET')
def item_list(request, vendor, state=None, include_box_items=False):
    items = Item.objects.filter(vendor__id=vendor)
    if state is not None:
        items = items.filter(state=state)
    if not include_box_items:
        items = items.filter(box__isnull=True)
    return [i.as_dict() for i in items]


@ajax_func('^box/list$', method='GET')
def box_list(request, vendor):
    out_boxes = []
    boxes = Box.objects.filter(item__vendor__id=vendor, item__hidden=False).distinct()
    for box in boxes:
        data = box.as_dict()
        items = box.get_items()
        data["items_brought_total"] = items.filter(state__in=(Item.BROUGHT, Item.STAGED, Item.SOLD, Item.RETURNED))\
            .count()
        data["items_sold"] = items.filter(state=Item.SOLD).count()
        data["items_returnable"] = items.filter(state__in=(Item.BROUGHT, Item.STAGED)).count()
        out_boxes.append(data)
    return out_boxes


@ajax_func('^item/checkin$')
def item_checkin(request, code):
    return item_mode_change(code, Item.ADVERTISED, Item.BROUGHT)


@ajax_func('^item/checkout$')
def item_checkout(request, code):
    return item_mode_change(code, (Item.BROUGHT, Item.ADVERTISED), Item.RETURNED, _(u"Item was not brought to event."))


@ajax_func('^item/compensate$')
def item_compensate(request, code):
    return item_mode_change(code, Item.SOLD, Item.COMPENSATED)


@ajax_func('^vendor/get$', method='GET')
def vendor_get(request, id):
    try:
        vendor = Vendor.objects.get(pk=int(id))
    except (ValueError, Vendor.DoesNotExist):
        raise AjaxError(RET_BAD_REQUEST, _(u"Invalid vendor id"))
    else:
        return vendor.as_dict()


@ajax_func('^vendor/find$', method='GET')
def vendor_find(request, q):
    clauses = [Q(vendor__isnull=False)]

    for part in q.split():
        clause = (
              Q(**UserAdapter.phone_query(part))
            | Q(username__icontains=part)
            | Q(first_name__icontains=part)
            | Q(last_name__icontains=part)
            | Q(email__icontains=part)
        )
        try:
            clause = clause | Q(vendor__id=int(part))
        except ValueError:
            pass

        clauses.append(clause)

    return [
        u.vendor.as_dict()
        for u in get_user_model().objects.filter(*clauses).all()
    ]


@ajax_func('^receipt/start$', atomic=True)
def receipt_start(request):
    receipt = Receipt()
    receipt.clerk = get_clerk(request)
    receipt.counter = get_counter(request)

    receipt.save()

    request.session["receipt"] = receipt.pk
    return receipt.as_dict()


@ajax_func('^item/reserve$', atomic=True)
def item_reserve(request, code):
    item = _get_item_or_404(code)
    receipt_id = request.session["receipt"]
    receipt = get_object_or_404(Receipt, pk=receipt_id)

    message = raise_if_item_not_available(item)
    if item.state in (Item.ADVERTISED, Item.BROUGHT, Item.MISSING):
        ItemStateLog.objects.log_state(item, Item.STAGED)
        item.state = Item.STAGED
        item.save()

        ReceiptItem.objects.create(item=item, receipt=receipt)
        # receipt.items.create(item=item)
        receipt.calculate_total()
        receipt.save()

        ret = item.as_dict()
        ret.update(total=receipt.total_cents)
        if message is not None:
            ret.update(_message=message)
        return ret
    else:
        # Not in expected state.
        raise AjaxError(RET_CONFLICT)


@ajax_func('^item/release$', atomic=True)
def item_release(request, code):
    item = _get_item_or_404(code)
    receipt_id = request.session["receipt"]
    remove_form = ItemRemoveForm({
        'receipt': receipt_id,
        'item': code,
    })
    if not remove_form.is_valid():
        raise AjaxError(RET_CONFLICT, ", ".join(remove_form.errors))

    remove_form.save()
    return remove_form.removal_entry.as_dict()


@ajax_func('^receipt/finish$', atomic=True)
def receipt_finish(request):
    receipt_id = request.session["receipt"]
    receipt = get_object_or_404(Receipt, pk=receipt_id)
    if receipt.status != Receipt.PENDING:
        raise AjaxError(RET_CONFLICT)

    receipt.sell_time = now()
    receipt.status = Receipt.FINISHED
    receipt.save()

    receipt_items = Item.objects.filter(receipt=receipt, receiptitem__action=ReceiptItem.ADD)
    for item in receipt_items:
        ItemStateLog.objects.log_state(item=item, new_state=Item.SOLD)
    receipt_items.update(state=Item.SOLD)

    del request.session["receipt"]
    return receipt.as_dict()


@ajax_func('^receipt/abort$', atomic=True)
def receipt_abort(request):
    receipt_id = request.session["receipt"]
    receipt = get_object_or_404(Receipt, pk=receipt_id)

    if receipt.status != Receipt.PENDING:
        raise AjaxError(RET_CONFLICT)

    # For all ADDed items, add REMOVE-entries and return the real Item's back to available.
    added_items = ReceiptItem.objects.filter(receipt_id=receipt_id, action=ReceiptItem.ADD)
    for receipt_item in added_items.only("item"):
        item = receipt_item.item

        ReceiptItem(item=item, receipt=receipt, action=ReceiptItem.REMOVE).save()

        if item.state != Item.BROUGHT:
            ItemStateLog.objects.log_state(item=item, new_state=Item.BROUGHT)
            item.state = Item.BROUGHT
            item.save()

    # Update ADDed items to be REMOVED_LATER. This must be done after the real Items have
    # been updated, and the REMOVE-entries added, as this will change the result set of
    # the original added_items -query (to always return zero entries).
    added_items.update(action=ReceiptItem.REMOVED_LATER)

    # End the receipt. (Must be done after previous updates, so calculate_total calculates
    # correct sum.)
    receipt.sell_time = now()
    receipt.status = Receipt.ABORTED
    receipt.calculate_total()
    receipt.save()

    del request.session["receipt"]
    return receipt.as_dict()


def _get_receipt_data_with_items(**kwargs):
    receipt = get_object_or_404(Receipt, **kwargs)
    receipt_items = ReceiptItem.objects.filter(receipt_id=receipt.pk).order_by("add_time")

    data = receipt.as_dict()
    data["items"] = [item.as_dict() for item in receipt_items]
    return data


@ajax_func('^receipt$', method='GET')
def receipt_get(request):
    """
    Find receipt by receipt id or one item in the receipt.
    """
    if "id" in request.GET:
        receipt_id = int(request.GET.get("id"))
    elif "item" in request.GET:
        item_code = request.GET.get("item")
        receipt_id = get_object_or_404(ReceiptItem, item__code=item_code, action=ReceiptItem.ADD).receipt_id
    else:
        raise AjaxError(RET_BAD_REQUEST)
    return _get_receipt_data_with_items(pk=receipt_id)


@ajax_func('^receipt/activate$')
def receipt_activate(request):
    """
    Activate previously started pending receipt.
    """
    clerk = request.session["clerk"]
    receipt_id = int(request.POST.get("id"))
    data = _get_receipt_data_with_items(pk=receipt_id, clerk__id=clerk, status=Receipt.PENDING)
    request.session["receipt"] = receipt_id
    return data


@ajax_func('^receipt/list$', overseer=True)
def receipt_list(request):
    receipts = Receipt.objects.filter(status=Receipt.PENDING)
    return list(map(lambda i: i.as_dict(), receipts))


@ajax_func('^barcode$', counter=False, clerk=False)
def get_barcodes(request, codes=None):
    """
    Get barcode images for a code, or list of codes.

    :param codes: Either list of codes, or a string, encoded in Json string.
    :type codes: str
    :return: List of barcode images encoded in data-url.
    :rtype: list[str]
    """
    from .templatetags.kirppu_tags import barcode_dataurl
    from json import loads

    codes = loads(codes)
    if isinstance(codes, string_types):
        codes = [codes]

    # XXX: This does ignore the width assertion. Beware with style sheets...
    outs = [
        barcode_dataurl(code, "png", None)
        for code in codes
    ]
    return outs


@ajax_func('^item/abandon$')
def items_abandon(request, vendor):
    """
    Set all of the vendor's 'brought to event' and 'missing' items to abandoned
    The view is expected to refresh itself
    """
    Item.objects.filter(
        vendor__id=vendor,
        state__in=(Item.BROUGHT, Item.MISSING),
    ).update(abandoned=True)
    return


@ajax_func('^item/mark_lost$', overseer=True, atomic=True)
def item_mark_lost(request, code):
    item = get_object_or_404(Item, code=code)
    if item.state == Item.SOLD:
        raise AjaxError(RET_CONFLICT, u"Item is sold!")
    if item.state == Item.STAGED:
        raise AjaxError(RET_CONFLICT, u"Item is staged to be sold!")
    if item.abandoned:
        raise AjaxError(RET_CONFLICT, u"Item is abandoned.")

    item.lost_property = True
    item.save()
    return item.as_dict()


def iterate_logs(entries, hide_advertised=False, hide_sales=False):
    """ Iterate through ItemStateLog objects returning current sum of each type of object at each timestamp.

    Example of returned CVS: js_time, advertized, brought, unsold, money, compensated

    js_time is milliseconds from unix_epoch.
    advertized is the number of items registered to the event at any time.
    brought is the cumulative sum of all items brought to the event.
    unsold is the number of items physically at the event. Should aproach zero by the end of the event.
    money is the number of sold items not yet redeemed by the seller. Should aproach zero by the end of the event.
    compensated is the number of sold and unsold items redeemed by the seller. Should aproach brought.

    :param entries: iterator to ItemStateLog objects.
    :return: JSON presentation of the objects, one item at a time.

    """
    from datetime import datetime, timedelta
    import pytz

    advertised_status = (Item.ADVERTISED,)
    brought_status = (Item.BROUGHT, Item.STAGED, Item.SOLD, Item.MISSING, Item.RETURNED, Item.COMPENSATED)
    unsold_status = (Item.BROUGHT, Item.STAGED)
    money_status = (Item.SOLD,)
    compensated_status = (Item.COMPENSATED, Item.RETURNED)
    unix_epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)

    def datetime_to_js_time(dt):
        return int((dt - unix_epoch).total_seconds() * 1000)

    def get_log_str(bucket_time, balance):
        entry_time = datetime_to_js_time(bucket_time)
        advertised = sum(balance[status] for status in advertised_status)
        brought = sum(balance[status] for status in brought_status)
        unsold = sum(balance[status] for status in unsold_status)
        money = sum(balance[status] for status in money_status)
        compensated = sum(balance[status] for status in compensated_status)
        return '%d,%s,%s,%s,%s,%s\n' % (
            entry_time,
            advertised if not hide_advertised else '',
            brought if not hide_sales else '',
            unsold if not hide_sales else '',
            money if not hide_sales else '',
            compensated if not hide_sales else '',
        )

    # Collect the data into buckets of size bucket_td to reduce the amount of data that has to be sent
    # and parsed at client side.
    balance = { item_type: 0 for item_type, _item_desc in Item.STATE }
    bucket_time = None
    bucket_td = timedelta(seconds=60)

    for entry in entries:
        if bucket_time is None:
            bucket_time = entry.time
            # Start the graph before the first entry, such that everything starts at zero.
            yield get_log_str(bucket_time - bucket_td, balance)
        if (entry.time - bucket_time) > bucket_td:
            # Fart out what was in the old bucket and start a new bucket.
            yield get_log_str(bucket_time, balance)
            bucket_time = entry.time

        if entry.old_state:
            balance[entry.old_state] -= 1
        balance[entry.new_state] += 1

    # Fart out the last bucket.
    if bucket_time is not None:
        yield get_log_str(bucket_time, balance)


@ajax_func('^stats/get_sales_data$', method='GET')
def stats_sales_data(request):
    entries = ItemStateLog.objects.exclude(new_state=Item.ADVERTISED)
    log_generator = iterate_logs(entries, hide_advertised=True)
    return StreamingHttpResponse(log_generator, content_type='text/csv')


@ajax_func('^stats/get_registration_data$', method='GET')
def stats_registration_data(request):
    entries = ItemStateLog.objects.filter(new_state=Item.ADVERTISED)
    log_generator = iterate_logs(entries, hide_sales=True)
    return StreamingHttpResponse(log_generator, content_type='text/csv')
