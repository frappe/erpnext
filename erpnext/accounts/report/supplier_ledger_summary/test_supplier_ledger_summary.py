import frappe
from frappe.utils import today

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	BLANK_ACCOUNTING_DIMENSION,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.supplier_ledger_summary.supplier_ledger_summary import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierLedgerSummary(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.supplier = "_Test Supplier"
		self.item = "_Test Item"

	def create_purchase_invoice(self, do_not_submit=False):
		frappe.set_user("Administrator")
		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			do_not_save=1,
			rate=300,
			price_list_rate=300,
			qty=1,
		)

		pi = pi.save()
		if not do_not_submit:
			pi = pi.submit()
		return pi

	def test_blank_supplier_group_filter(self):
		invoice = self.create_purchase_invoice()
		group = frappe.db.get_value("Supplier", self.supplier, "supplier_group")
		parent_group = frappe.db.get_value("Supplier Group", group, "parent_supplier_group")
		filters = frappe._dict(
			company=self.company,
			party=self.supplier,
			from_date=invoice.posting_date,
			to_date=invoice.posting_date,
		)
		for party_group in (None, "", group):
			frappe.db.set_value("Supplier", self.supplier, "supplier_group", party_group)
			for groups, expected in (
				([BLANK_ACCOUNTING_DIMENSION], int(not party_group)),
				([parent_group], int(bool(party_group))),
				([BLANK_ACCOUNTING_DIMENSION, parent_group], 1),
			):
				with self.subTest(party_group=party_group, groups=groups):
					filters.supplier_group = groups
					rows = execute(filters)[1]
					self.assertEqual(len(rows), expected)
					if rows:
						self.assertEqual(rows[0].invoiced_amount, invoice.grand_total)

	def test_blank_cost_center_filter(self):
		blank_invoice = self.create_purchase_invoice()
		cost_center = blank_invoice.items[0].cost_center
		invoice = self.create_purchase_invoice(do_not_submit=True)
		invoice.cost_center = cost_center
		invoice.save().submit()
		parent_cost_center = frappe.db.get_value("Cost Center", cost_center, "parent_cost_center")
		filters = frappe._dict(
			company=self.company,
			party=self.supplier,
			from_date=blank_invoice.posting_date,
			to_date=blank_invoice.posting_date,
		)

		for blank_value in (None, ""):
			frappe.db.set_value("GL Entry", {"voucher_no": blank_invoice.name}, "cost_center", blank_value)
			for cost_centers, expected in (
				([BLANK_ACCOUNTING_DIMENSION], 300),
				([cost_center], 300),
				([BLANK_ACCOUNTING_DIMENSION, parent_cost_center], 600),
			):
				with self.subTest(blank_value=blank_value, cost_centers=cost_centers):
					filters.cost_center = cost_centers
					rows = execute(filters)[1]
					self.assertEqual(len(rows), 1)
					self.assertEqual(rows[0].invoiced_amount, expected)

	def test_basic_supplier_ledger_summary(self):
		self.create_purchase_invoice()

		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		expected = {
			"party": "_Test Supplier",
			"party_name": "_Test Supplier",
			"opening_balance": 0,
			"invoiced_amount": 300.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 300.0,
			"currency": "INR",
			"supplier_name": "_Test Supplier",
		}

		report_output = execute(filters)[1]
		self.assertEqual(len(report_output), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report_output[0].get(field), expected.get(field))

	def test_supplier_ledger_summary_with_filters(self):
		self.create_purchase_invoice()

		supplier_group = frappe.db.get_value("Supplier", self.supplier, "supplier_group")

		filters = {
			"company": self.company,
			"from_date": today(),
			"to_date": today(),
			"supplier_group": supplier_group,
		}

		expected = {
			"party": "_Test Supplier",
			"party_name": "_Test Supplier",
			"opening_balance": 0,
			"invoiced_amount": 300.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 300.0,
			"currency": "INR",
			"supplier_name": "_Test Supplier",
		}

		report_output = execute(filters)[1]
		self.assertEqual(len(report_output), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report_output[0].get(field), expected.get(field))
