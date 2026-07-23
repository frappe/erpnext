# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.utils import (
	_check_credit_limit_warn,
	_check_packed_qty_warn,
)
from erpnext.selling.doctype.customer.test_customer import set_credit_limit
from erpnext.tests.utils import ERPNextTestSuite


def _get_orange_warnings():
	return [m for m in frappe.message_log if m.get("indicator") == "orange"]


class _CreditLimitBase(ERPNextTestSuite):
	COMPANY = "_Test Company"
	CUSTOMER = "_Test Customer"
	CREDIT_LIMIT = 100.0
	OVER = 200.0
	UNDER = 50.0

	def setUp(self):
		set_credit_limit(self.CUSTOMER, self.COMPANY, self.CREDIT_LIMIT)
		frappe.message_log.clear()


class TestCreditLimitWarnSalesInvoice(_CreditLimitBase):
	def _make_si(self, amount, is_return=0):
		"""Build an in-memory (unsaved) draft SI."""
		si = frappe.new_doc("Sales Invoice")
		si.company = self.COMPANY
		si.customer = self.CUSTOMER
		si.is_return = is_return
		si.base_grand_total = amount
		si.append("items", {"item_code": "_Test Item", "qty": 1, "rate": amount})
		return si

	def test_warns_when_amount_exceeds_credit_limit(self):
		"""Orange warning must appear when base_grand_total > credit_limit."""
		si = self._make_si(self.OVER)
		_check_credit_limit_warn(si)
		self.assertTrue(_get_orange_warnings(), "Expected an orange credit-limit warning")

	def test_no_warning_when_amount_within_credit_limit(self):
		"""No warning when base_grand_total is safely within the credit limit."""
		si = self._make_si(self.UNDER)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_for_return_invoices(self):
		"""Credit limit check is skipped entirely for return transactions."""
		si = self._make_si(self.OVER, is_return=1)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_customer_has_no_credit_limit(self):
		"""If the customer has no credit limit configured, no warning is shown."""
		frappe.db.delete("Customer Credit Limit", {"parent": self.CUSTOMER})
		si = self._make_si(self.OVER)
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_all_items_linked_to_so_or_dn(self):
		"""
		When every item on the SI already has a sales_order or delivery_note
		reference, the check is skipped (the SO/DN already counted this amount).
		"""
		si = self._make_si(self.OVER)
		si.items[0].sales_order = "SO-TEST-0001"
		_check_credit_limit_warn(si)
		self.assertFalse(_get_orange_warnings())


class TestCreditLimitWarnSalesOrder(_CreditLimitBase):
	def _make_so(self, amount):
		"""Build an in-memory (unsaved) draft SO."""
		so = frappe.new_doc("Sales Order")
		so.company = self.COMPANY
		so.customer = self.CUSTOMER
		so.base_grand_total = amount
		so.append("items", {"item_code": "_Test Item", "qty": 1, "rate": amount})
		return so

	def test_warns_on_first_save_when_limit_exceeded(self):
		so = self._make_so(self.OVER)
		self.assertTrue(so.is_new(), "Doc should be new (not yet in DB)")
		_check_credit_limit_warn(so)
		self.assertTrue(_get_orange_warnings())

	def test_warns_when_amount_exceeds_credit_limit(self):
		so = self._make_so(self.OVER)
		_check_credit_limit_warn(so)
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_amount_within_credit_limit(self):
		so = self._make_so(self.UNDER)
		_check_credit_limit_warn(so)
		self.assertFalse(_get_orange_warnings())

	def test_no_warning_when_bypass_is_set(self):
		"""
		When bypass_credit_limit_check=1 on the Customer Credit Limit row,
		SO's check_credit_limit skips entirely.
		"""
		frappe.db.set_value(
			"Customer Credit Limit",
			{"parent": self.CUSTOMER, "company": self.COMPANY},
			"bypass_credit_limit_check",
			1,
		)
		so = self._make_so(self.OVER)
		_check_credit_limit_warn(so)
		self.assertFalse(_get_orange_warnings())


class TestCreditLimitWarnDeliveryNote(_CreditLimitBase):
	def _make_dn(self, amount, bypass=False, against_sales_order=None, against_sales_invoice=None):
		"""Build an in-memory (unsaved) draft DN."""
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.COMPANY
		dn.customer = self.CUSTOMER
		dn.base_grand_total = amount
		dn.base_net_total = amount
		item = {
			"item_code": "_Test Item",
			"qty": 1,
			"rate": amount,
			"amount": amount,
			"base_amount": amount,
		}
		if against_sales_order:
			item["against_sales_order"] = against_sales_order
		if against_sales_invoice:
			item["against_sales_invoice"] = against_sales_invoice
		dn.append("items", item)

		if bypass:
			frappe.db.set_value(
				"Customer Credit Limit",
				{"parent": self.CUSTOMER, "company": self.COMPANY},
				"bypass_credit_limit_check",
				1,
			)

		return dn

	def test_bypass_false_warns_for_existing_draft(self):
		"""bypass=False, existing draft: proportional extra_amount path still applies."""
		dn = self._make_dn(self.OVER)
		_check_credit_limit_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_bypass_false_no_warning_when_under_limit(self):
		dn = self._make_dn(self.UNDER)
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_bypass_false_no_warning_when_all_items_linked_to_so(self):
		"""
		Items fully linked to a SO are excluded from unlinked_net.
		extra_amount becomes 0 → check is skipped.
		"""
		dn = self._make_dn(self.OVER, against_sales_order="SO-TEST-0001")
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_bypass_false_partial_link_warns_proportionally(self):
		"""
		Two items: one linked to SO, one unlinked.
		Only the unlinked portion should count toward the credit limit check.
		"""
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.COMPANY
		dn.customer = self.CUSTOMER
		dn.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 60, "amount": 60, "base_amount": 60})
		dn.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 50,
				"amount": 50,
				"base_amount": 50,
				"against_sales_order": "SO-TEST-0001",
			},
		)
		dn.base_net_total = 110
		dn.base_grand_total = 110

		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings(), "60 < 100 credit limit, should not warn")

	# bypass=True -----------------------------------------------------------

	def test_bypass_true_warns_on_first_save_new_doc(self):
		"""
		bypass=True: existing doc.check_credit_limit() handles extra_amount
		internally (base_grand_total for items not against SI).
		"""
		dn = self._make_dn(self.OVER, bypass=True)
		self.assertTrue(dn.is_new())
		_check_credit_limit_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_bypass_true_no_warning_when_all_items_billed(self):
		"""
		bypass=True: items already linked to a SI are excluded from extra_amount.
		If all items have against_sales_invoice set, extra_amount=0 → no check.
		"""
		dn = self._make_dn(self.OVER, bypass=True, against_sales_invoice="SINV-TEST-0001")
		_check_credit_limit_warn(dn)
		self.assertFalse(_get_orange_warnings())


# ---------------------------------------------------------------------------
# Packed Qty
# ---------------------------------------------------------------------------


class TestPackedQtyWarn(ERPNextTestSuite):
	COMPANY = "_Test Company"
	CUSTOMER = "_Test Customer"

	def setUp(self):
		frappe.message_log.clear()

	def _make_dn(self):
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.COMPANY
		dn.customer = self.CUSTOMER
		dn.append(
			"items",
			{"item_code": "_Test Item", "qty": 2, "rate": 100, "amount": 200, "base_amount": 200},
		)
		return dn

	def test_no_warning_for_new_doc(self):
		"""New doc has no packing slip in DB, so validate_packed_qty is skipped."""
		dn = self._make_dn()
		_check_packed_qty_warn(dn)
		self.assertFalse(_get_orange_warnings())

	def test_warns_when_packed_qty_mismatches(self):
		"""When validate_packed_qty raises, an orange warning is produced."""
		dn = self._make_dn()
		with patch.object(
			dn,
			"validate_packed_qty",
			side_effect=frappe.ValidationError("Packed Qty must be equal to qty"),
		):
			_check_packed_qty_warn(dn)
		self.assertTrue(_get_orange_warnings())

	def test_no_warning_when_packed_qty_matches(self):
		"""When validate_packed_qty passes silently, no warning is produced."""
		dn = self._make_dn()
		with patch.object(dn, "validate_packed_qty", return_value=None):
			_check_packed_qty_warn(dn)
		self.assertFalse(_get_orange_warnings())
