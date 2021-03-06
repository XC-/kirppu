# -*- coding: utf-8 -*-
import decimal

from django.test import Client
from django.test import TestCase
from django.test import override_settings

from kirppu.provision import Provision

from .factories import *
from .api_access import apiOK

__author__ = 'codez'


class SoldItemFactory(ItemFactory):
    state = Item.SOLD


class ProvisionTest(TestCase):
    def setUp(self):
        self.vendor = VendorFactory()

    def test_no_items_no_provision(self):
        p = Provision(self.vendor.id, provision_function=lambda _: None)

        self.assertFalse(p.has_provision)
        self.assertIsNone(p.provision_fix)
        self.assertIsNone(p.provision)

    def test_no_items_with_provision(self):
        p = Provision(self.vendor.id, provision_function=lambda _: Decimal("0.10"))

        self.assertFalse(p.has_provision)
        self.assertIsNone(p.provision_fix)
        self.assertIsNone(p.provision)

    """def test_no_items_with_provision_already_compensated(self):
        some_items = ItemFactory.create_batch(10, vendor=self.vendor, state=Item.COMPENSATED)

        p = Provision(self.vendor.id, provision_function=lambda q: Decimal("0.10") * len(q))

        self.assertTrue(p.has_provision)
        self.assertEqual(p.provision_fix, Decimal("-1.00"))
        self.assertIn(p.provision, (None, Decimal("0.00")))
        # FIXME: Failing. This should be either None/0 or -1, but which?"""


class BeforeProvisionTest(TestCase):
    def setUp(self):
        self.vendor = VendorFactory()
        self.items = SoldItemFactory.create_batch(10, vendor=self.vendor)

    def test_no_provision_before_compensation(self):
        p = Provision(self.vendor.id, provision_function=lambda _: None)

        self.assertEqual(len(p._vendor_items), len(self.items))
        self.assertFalse(p.has_provision)
        self.assertIsNone(p.provision)
        self.assertIsNone(p.provision_fix)

    def test_simple_provision_before_compensation(self):
        p = Provision(self.vendor.id, provision_function=lambda q: Decimal("0.10") * len(q))

        self.assertEqual(len(p._vendor_items), len(self.items))
        self.assertTrue(p.has_provision)
        self.assertEqual(p.provision_fix, Decimal("0.00"))
        self.assertEqual(p.provision, Decimal("-1.00"))  # -(10 * 0.10) == -1

    def test_missing_provision(self):
        some_items = ItemFactory.create_batch(10, vendor=self.vendor, state=Item.COMPENSATED)

        p = Provision(self.vendor.id, provision_function=lambda q: Decimal("0.10") * len(q))

        self.assertTrue(p.has_provision)
        self.assertEqual(p.provision_fix, Decimal("-1.00"))
        self.assertEqual(p.provision, Decimal("-1.00"))


class FinishingProvisionTest(TestCase):
    def setUp(self):
        self.vendor = VendorFactory()
        self.receipt = ReceiptFactory(type=Receipt.TYPE_COMPENSATION)
        self.items = ReceiptItemFactory.create_batch(
            10, receipt=self.receipt, item__vendor=self.vendor, item__state=Item.COMPENSATED)

    def test_no_provision_finishing_compensation(self):
        p = Provision(self.vendor.id, receipt=self.receipt, provision_function=lambda _: None)

        self.assertEqual(len(p._vendor_items), len(self.items))
        self.assertFalse(p.has_provision)
        self.assertIsNone(p.provision)
        self.assertIsNone(p.provision_fix)

    def test_simple_provision_finishing_compensation(self):
        p = Provision(self.vendor.id, receipt=self.receipt, provision_function=lambda q: Decimal("0.10") * len(q))

        self.assertEqual(len(p._vendor_items), len(self.items))
        self.assertTrue(p.has_provision)
        self.assertEqual(p.provision_fix, Decimal("0.00"))
        self.assertEqual(p.provision, Decimal("-1.00"))  # -(10 * 0.10) == -1

    def test_concurrent_sell_finishing_compensation(self):
        more_items = SoldItemFactory.create_batch(10, vendor=self.vendor)

        p = Provision(self.vendor.id, receipt=self.receipt, provision_function=lambda q: Decimal("0.10") * len(q))

        still_more_items = SoldItemFactory.create_batch(10, vendor=self.vendor)

        self.assertTrue(p.has_provision)
        self.assertEqual(p.provision_fix, Decimal("0.00"))
        self.assertEqual(p.provision, Decimal("-1.00"))  # -(10 * 0.10) == -1


class ApiProvisionTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.vendor = VendorFactory()
        self.items = SoldItemFactory.create_batch(10, vendor=self.vendor)

        self.counter = CounterFactory()
        self.clerk = ClerkFactory()

        apiOK.clerk_login(self.client, {"code": self.clerk.get_code(), "counter": self.counter.identifier})

    def tearDown(self):
        apiOK.clerk_logout(self.client)

    def _compensate(self, items):
        receipt = apiOK.item_compensate_start(self.client, {"vendor": self.vendor.id})

        for item in items:
            apiOK.item_compensate(self.client, {"code": item.code})

        response = apiOK.item_compensate_end(self.client)
        receipt = response.json()
        return receipt, response

    def _get_extra(self, extras, extra_type):
        e = [item for item in extras if item["type"] == extra_type]
        self.assertTrue(len(e) <= 1)
        if not e:
            return None
        return e[0]

    def _get_receipt(self, receipt_id):
        receipt = apiOK.receipt_get(self.client, {"id": receipt_id, "type": "compensation"})
        extras = [item for item in receipt.json()["items"] if item["action"] == "EXTRA"]
        return extras

    # region No Provision
    @override_settings(KIRPPU_POST_PROVISION=lambda query: None)
    def test_no_provision_no_items(self):
        receipt, response = self._compensate([])
        self.assertEqual(receipt["total"], 0)

    @override_settings(KIRPPU_POST_PROVISION=lambda query: None)
    def test_no_provision_single_go(self):
        receipt, response = self._compensate(self.items)
        self.assertEqual(receipt["total"], 1250)  # 10*1.25 as cents

    @override_settings(KIRPPU_POST_PROVISION=lambda query: None)
    def test_no_provision_two_phases(self):
        part_1 = self.items[:6]
        part_2 = self.items[6:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 750)  # 6*1.25 as cents

        receipt_2, response_2 = self._compensate(part_2)
        self.assertEqual(receipt_2["total"], 500)  # 4*1.25 as cents
        # 750 + 500 == 1250
    # endregion

    # region Linear Provision
    @override_settings(KIRPPU_POST_PROVISION=lambda query: Decimal("0.10") * len(query))
    def test_linear_provision_no_items(self):
        receipt, response = self._compensate([])
        self.assertEqual(receipt["total"], 0)

    @override_settings(KIRPPU_POST_PROVISION=lambda query: Decimal("0.10") * len(query))
    def test_linear_provision_single_go(self):
        guess = apiOK.compensable_items(self.client, {"vendor": self.vendor.id})
        provision = self._get_extra(guess.json()["extras"], "PRO")
        self.assertEqual(provision["value"], -100)

        receipt, response = self._compensate(self.items)
        self.assertEqual(receipt["total"], 1150)  # 10*(1.25-0.10) as cents

    @override_settings(KIRPPU_POST_PROVISION=lambda query: Decimal("0.10") * len(query))
    def test_linear_provision_two_phases(self):
        part_1 = self.items[:6]
        part_2 = self.items[6:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 690)  # 6*(1.25-0.10) as cents

        receipt_2, response_2 = self._compensate(part_2)
        self.assertEqual(receipt_2["total"], 460)  # 4*(1.25-0.10) as cents
        # 690 + 460 == 1150
    # endregion

    # region Step Provision
    @override_settings(KIRPPU_POST_PROVISION=lambda query: Decimal("0.50") * (len(query) // 4))
    def test_step_provision_single_go(self):
        guess = apiOK.compensable_items(self.client, {"vendor": self.vendor.id})
        provision = self._get_extra(guess.json()["extras"], "PRO")
        self.assertEqual(provision["value"], -100)

        receipt, response = self._compensate(self.items)
        self.assertEqual(receipt["total"], 1150)  # 10*1.25-(10//4)*0.50 as cents

    @override_settings(KIRPPU_POST_PROVISION=lambda query: Decimal("0.50") * (len(query) // 4))
    def test_step_provision_two_phases(self):
        part_1 = self.items[:6]
        part_2 = self.items[6:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 700)  # 6*1.25-0.50 as cents

        receipt_2, response_2 = self._compensate(part_2)
        self.assertEqual(receipt_2["total"], 450)  # 4*1.25-0.50 as cents
        # 700 + 450 == 1150

        # Ensure there is no fixup entry in the item set.
        extras = [item["type"] for item in self._get_receipt(receipt_2["id"])]
        self.assertEqual(len(extras), 1)
        self.assertIn("PRO", extras)
        self.assertNotIn("PRO_FIX", extras)
    # endregion

    @staticmethod
    def round(value):
        """
        Round given decimal value to next 50 cents.
        """
        value = value.quantize(Decimal('0.1'), rounding=decimal.ROUND_UP)
        remainder = value % Decimal('.5')
        if remainder > Decimal('0'):
            value += Decimal('.5') - remainder
        return value

    # region Rounding Provision
    @override_settings(KIRPPU_POST_PROVISION=lambda query: ApiProvisionTest.round(Decimal("0.20") * len(query)))
    def test_rounding_provision_single_go(self):
        guess = apiOK.compensable_items(self.client, {"vendor": self.vendor.id}).json()["extras"]
        provision = self._get_extra(guess, "PRO")
        self.assertEqual(provision["value"], -200)
        self.assertIsNone(self._get_extra(guess, "PRO_FIX"))

        receipt, response = self._compensate(self.items)
        self.assertEqual(receipt["total"], 1050)  # 10*1.25-10*0.20 as cents

    @override_settings(KIRPPU_POST_PROVISION=lambda query: ApiProvisionTest.round(Decimal("0.20") * len(query)))
    def test_rounding_provision_two_phases(self):
        part_1 = self.items[:6]
        part_2 = self.items[6:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 600)  # 6*1.25-1.50 as cents

        receipt_2, response_2 = self._compensate(part_2)
        receipt = self._get_receipt(receipt_2["id"])

        self.assertEqual(receipt_2["total"], 450)  # 4*1.25-2*0.50 as cents
        # 600 + 450 == 1050

        receipt = self._get_receipt(receipt_2["id"])
        extras = [item["type"] for item in receipt]
        self.assertEqual(len(extras), 1)
        self.assertIn("PRO", extras)
        self.assertNotIn("PRO_FIX", extras)

    @override_settings(KIRPPU_POST_PROVISION=lambda query: ApiProvisionTest.round(Decimal("0.20") * len(query)))
    def test_rounding_provision_two_phases_2(self):
        part_1 = self.items[:5]
        part_2 = self.items[5:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 525)  # 5*1.25-1.00 as cents

        receipt_2, response_2 = self._compensate(part_2)
        receipt = self._get_receipt(receipt_2["id"])

        self.assertEqual(receipt_2["total"], 525)  # 5*1.25-2*0.50 as cents

        receipt = self._get_receipt(receipt_2["id"])
        extras = [item["type"] for item in receipt]
        self.assertEqual(len(extras), 1)
        self.assertIn("PRO", extras)
        self.assertNotIn("PRO_FIX", extras)

    @override_settings(KIRPPU_POST_PROVISION=lambda query: ApiProvisionTest.round(Decimal("0.20") * len(query)))
    def test_rounding_provision_two_phases_3(self):
        part_1 = self.items[:4]
        part_2 = self.items[4:]

        receipt_1, response_1 = self._compensate(part_1)
        self.assertEqual(receipt_1["total"], 400)  # 4*1.25-1.00 as cents

        receipt_2, response_2 = self._compensate(part_2)
        receipt = self._get_receipt(receipt_2["id"])

        self.assertEqual(receipt_2["total"], 650)  # 6*1.25-2*0.50 as cents
        # 400 + 650 == 1050

        receipt = self._get_receipt(receipt_2["id"])
        extras = [item["type"] for item in receipt]
        self.assertEqual(len(extras), 1)
        self.assertIn("PRO", extras)
        self.assertNotIn("PRO_FIX", extras)

    @override_settings(KIRPPU_POST_PROVISION=lambda query: ApiProvisionTest.round(Decimal("0.20") * len(query)))
    def test_rounding_provision_with_add(self):
        guess = apiOK.compensable_items(self.client, {"vendor": self.vendor.id}).json()["extras"]
        provision = self._get_extra(guess, "PRO")
        self.assertEqual(provision["value"], -200)
        self.assertIsNone(self._get_extra(guess, "PRO_FIX"))

        receipt_1, response_1 = self._compensate(self.items)
        self.assertEqual(receipt_1["total"], 1050)

        more = SoldItemFactory.create_batch(4, vendor=self.vendor)
        guess = apiOK.compensable_items(self.client, {"vendor": self.vendor.id}).json()["extras"]
        provision = self._get_extra(guess, "PRO")
        self.assertEqual(provision["value"], -100)
        self.assertIsNone(self._get_extra(guess, "PRO_FIX"))

        receipt_2, response_2 = self._compensate(more)
        receipt = self._get_receipt(receipt_2["id"])

        self.assertEqual(receipt_2["total"], 400)
# [<-needed for ide-region]
    # endregion
