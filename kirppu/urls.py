from __future__ import unicode_literals, print_function, absolute_import
from django.conf.urls import url
from django.conf import settings
from django.utils.six import itervalues

from .views import (
    get_clerk_codes,
    get_counter_commands,
    checkout_view,
    overseer_view,
    vendor_view,
    accept_terms,
    get_items,
    all_to_print,
    item_add,
    item_hide,
    item_to_printed,
    item_to_not_printed,
    item_update_name,
    item_update_type,
    item_update_price,
    remove_item_from_receipt,
    get_boxes,
    box_add,
    box_content,
    box_hide,
    box_print,
    stats_view,
    lost_and_found_list,
)
from .checkout_api import AJAX_FUNCTIONS, checkout_js

__author__ = 'jyrkila'

_urls = [
    url(r'^clerks/$', get_clerk_codes, name='clerks'),
    url(r'^commands/$', get_counter_commands, name='commands'),
    url(r'^checkout/$', checkout_view, name='checkout_view'),
    url(r'^overseer/$', overseer_view, name='overseer_view'),
    url(r'^stats/$', stats_view, name='stats_view'),
    url(r'^vendor/$', vendor_view, name='vendor_view'),
    url(r'^vendor/accept_terms$', accept_terms, name='accept_terms'),
    url(r'^vendor/items/$', get_items, name='page'),
    url(r'^vendor/items/move_to_print$', all_to_print, name='all_to_print'),
    url(r'^vendor/item/$', item_add, name='item_add'),
    url(r'^vendor/item/(?P<code>\w+?)/to_printed$', item_to_printed, name='item_to_printed'),
    url(r'^vendor/item/(?P<code>\w+?)/price$', item_update_price, name='item_update_price'),
    url(r'^vendor/item/(?P<code>\w+?)/name$', item_update_name, name='item_update_name'),
    url(r'^vendor/item/(?P<code>\w+?)/type$', item_update_type, name='item_update_type'),
    url(r'^vendor/item/(?P<code>\w+?)/to_not_printed$', item_to_not_printed, name='item_to_not_printed'),
    url(r'^vendor/item/(?P<code>\w+?)/hide$', item_hide, name='item_hide'),
    url(r'^remove_item', remove_item_from_receipt, name='remove_item_from_receipt'),
    url(r'^lost_and_found/$', lost_and_found_list, name='lost_and_found'),
    url(r'^vendor/boxes/$', get_boxes, name='vendor_boxes'),
    url(r'^vendor/box/$', box_add, name='box_add'),
    url(r'^vendor/box/(?P<box_id>\w+?)/content$', box_content, name='box_content'),
    url(r'^vendor/box/(?P<box_id>\w+?)/hide$', box_hide, name='box_hide'),
    url(r'^vendor/box/(?P<box_id>\w+?)/print', box_print, name='box_print'),
]

if settings.KIRPPU_CHECKOUT_ACTIVE:  # Only activate API when checkout is active.
    _urls.append(url('^api/checkout.js$', checkout_js, name='checkout_js'))

_urls.extend([
    url(func.url, func.pkg + "." + func.name, name=func.view_name)
    for func in itervalues(AJAX_FUNCTIONS)
    if func.is_public or settings.KIRPPU_CHECKOUT_ACTIVE
])

urlpatterns = _urls
