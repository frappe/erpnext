# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.selling.doctype.customer.test_customer import set_credit_limit
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class _CreditLimitBase(ERPNextTestSuite):
	COMPANY = "_Test Company"
	CUSTOMER = "_Test Customer"
	CREDIT_LIMIT = 100.0
	OVER = 200.0
	UNDER = 50.0

	def setUp(self):
		set_credit_limit(self.CUSTOMER, self.COMPANY, self.CREDIT_LIMIT)

	def _assert_credit(self, doc, *, raises, **kwargs):
		if raises:
			with self.assertRaises(frappe.ValidationError):
				doc.check_credit_limit(**kwargs)
		else:
			doc.check_credit_limit(**kwargs)


class TestCreditLimitWarnSalesInvoice(_CreditLimitBase):
	def _make_si(self, amount, is_return=0, sales_order=None):
		si = frappe.new_doc("Sales Invoice")
		si.company = self.COMPANY
		si.customer = self.CUSTOMER
		si.is_return = is_return
		si.base_grand_total = amount
		item = {"item_code": "_Test Item", "qty": 1, "rate": amount}
		if sales_order:
			item["sales_order"] = sales_order
		si.append("items", item)
		return si

	def test_warns_when_amount_exceeds_credit_limit(self):
		si = self._make_si(self.OVER)
		self._assert_credit(si, raises=True, extra_amount=si.base_grand_total)

	def test_no_warning_when_amount_within_credit_limit(self):
		si = self._make_si(self.UNDER)
		self._assert_credit(si, raises=False, extra_amount=si.base_grand_total)

	def test_return_invoice_is_skipped(self):
		si = self._make_si(self.OVER, is_return=1)
		self._assert_credit(si, raises=False, extra_amount=si.base_grand_total)

	def test_no_warning_when_all_items_linked_to_so_or_dn(self):
		si = self._make_si(self.OVER, sales_order="SO-TEST-0001")
		self._assert_credit(si, raises=False, extra_amount=si.base_grand_total)

	def test_no_warning_when_customer_has_no_credit_limit(self):
		frappe.db.delete("Customer Credit Limit", {"parent": self.CUSTOMER})
		si = self._make_si(self.OVER)
		self._assert_credit(si, raises=False, extra_amount=si.base_grand_total)


class TestCreditLimitWarnSalesOrder(_CreditLimitBase):
	def _make_so(self, amount):
		so = frappe.new_doc("Sales Order")
		so.company = self.COMPANY
		so.customer = self.CUSTOMER
		so.base_grand_total = amount
		so.append("items", {"item_code": "_Test Item", "qty": 1, "rate": amount})
		return so

	def test_warns_when_amount_exceeds_credit_limit(self):
		so = self._make_so(self.OVER)
		self._assert_credit(so, raises=True, extra_amount=so.base_grand_total)

	def test_no_warning_when_amount_within_credit_limit(self):
		so = self._make_so(self.UNDER)
		self._assert_credit(so, raises=False, extra_amount=so.base_grand_total)

	def test_no_warning_when_bypass_is_set(self):
		frappe.db.set_value(
			"Customer Credit Limit",
			{"parent": self.CUSTOMER, "company": self.COMPANY},
			"bypass_credit_limit_check",
			1,
		)
		so = self._make_so(self.OVER)
		self._assert_credit(so, raises=False, extra_amount=so.base_grand_total)


class TestCreditLimitWarnDeliveryNote(_CreditLimitBase):
	def _make_dn(self, amount, bypass=False, against_sales_order=None, against_sales_invoice=None):
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.COMPANY
		dn.customer = self.CUSTOMER
		dn.base_grand_total = amount
		dn.base_net_total = amount
		item = {"item_code": "_Test Item", "qty": 1, "rate": amount, "amount": amount, "base_amount": amount}
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

	def test_bypass_false_warns_when_over_limit(self):
		dn = self._make_dn(self.OVER)
		self._assert_credit(dn, raises=True, preview=True)

	def test_bypass_false_no_warning_when_under_limit(self):
		dn = self._make_dn(self.UNDER)
		self._assert_credit(dn, raises=False, preview=True)

	def test_bypass_false_no_warning_when_all_items_linked_to_so(self):
		dn = self._make_dn(self.OVER, against_sales_order="SO-TEST-0001")
		self._assert_credit(dn, raises=False, preview=True)

	def test_bypass_false_partial_link_counts_only_unlinked_portion(self):
		# only the unlinked item's share counts toward the limit; 60 < 100 → no warning
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
		self._assert_credit(dn, raises=False, preview=True)

	def test_bypass_true_warns_when_unbilled(self):
		dn = self._make_dn(self.OVER, bypass=True)
		self._assert_credit(dn, raises=True, preview=True)

	def test_bypass_true_no_warning_when_all_items_billed(self):
		dn = self._make_dn(self.OVER, bypass=True, against_sales_invoice="SINV-TEST-0001")
		self._assert_credit(dn, raises=False, preview=True)


class TestDeliveryNotePrevDocstatus(ERPNextTestSuite):
	def _make_dn(self, sales_order, **item):
		dn = frappe.new_doc("Delivery Note")
		dn.company = "_Test Company"
		dn.customer = "_Test Customer"
		dn.currency = "INR"
		dn.append(
			"items",
			{"item_code": "_Test Item", "qty": 1, "rate": 100, "against_sales_order": sales_order, **item},
		)
		return dn

	def test_throws_when_referenced_sales_order_not_submitted(self):
		so = make_sales_order(do_not_submit=True)
		dn = self._make_dn(so.name)
		with self.assertRaises(frappe.ValidationError):
			dn.validate_with_previous_doc()

	def test_no_throw_when_referenced_sales_order_submitted(self):
		so = make_sales_order()
		dn = self._make_dn(so.name)
		dn.validate_with_previous_doc()

	def test_all_unsubmitted_refs_reported_in_single_message(self):
		so1 = make_sales_order(do_not_submit=True)
		so2 = make_sales_order(do_not_submit=True)
		dn = self._make_dn(so1.name)
		dn.append(
			"items", {"item_code": "_Test Item", "qty": 1, "rate": 100, "against_sales_order": so2.name}
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			dn.validate_with_previous_doc()
		self.assertIn(so1.name, str(cm.exception))
		self.assertIn(so2.name, str(cm.exception))
