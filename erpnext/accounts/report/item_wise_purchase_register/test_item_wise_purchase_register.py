import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.item_wise_purchase_register.item_wise_purchase_register import execute
from erpnext.accounts.report.item_wise_purchase_register import item_wise_purchase_register as report
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestItemWisePurchaseRegister(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_supplier()
		self.create_item()

	def tearDown(self):
		frappe.db.rollback()

	def create_purchase_invoice(self, do_not_submit=False):
		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			do_not_save=1,
			rate=100,
			price_list_rate=100,
			qty=1,
		)

		pi = pi.save()
		if not do_not_submit:
			pi = pi.submit()
		return pi

	def test_basic_report_output(self):
		pi = self.create_purchase_invoice()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"item_code": pi.items[0].item_code,
			"invoice": pi.name,
			"posting_date": getdate(),
			"supplier": pi.supplier,
			"credit_to": pi.credit_to,
			"company": self.company,
			"expense_account": pi.items[0].expense_account,
			"stock_qty": 1.0,
			"stock_uom": pi.items[0].stock_uom,
			"rate": 100.0,
			"amount": 100.0,
			"total_tax": 0,
			"total": 100.0,
			"currency": "INR",
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_execute_without_filters_TC_ACC_419(self):
		filters = frappe._dict({"company": self.company})
		cols, data, *_ = report._execute(filters)
		self.assertIsInstance(cols, list)
		self.assertIsInstance(data, list)

	def test_group_by_with_grand_total_TC_ACC_420(self):
		self.create_purchase_invoice()
		filters = frappe._dict({
		"from_date": today(),
		"to_date": today(),
		"company": self.company,
		"group_by": "Supplier",
		})
		cols, data, *_ = report._execute(filters)
		self.assertTrue(any("percent_gt" in row for row in data))

	def test_additional_table_columns_0TC_ACC_421(self):
		self.create_purchase_invoice()
		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		additional_columns = [{"fieldname": "supplier", "label": "Supp Name"}]
		cols, data, *_ = report._execute(filters, additional_table_columns=additional_columns)
		self.assertIn("supplier", data[0])
	
	def test_apply_conditions_item_code_and_group_TC_ACC_422(self):
		from frappe import _dict
		pi = frappe.qb.DocType("Purchase Invoice")
		pii = frappe.qb.DocType("Purchase Invoice Item")

		query = (
			frappe.qb.from_(pi)
			.join(pii)
			.on(pi.name == pii.parent)
			.select(pi.name, pii.item_code, pii.item_group)
		)
		filters = _dict({"item_code": "ITEM-001", "item_group": "Products"})
		query = report.apply_conditions(query, pi, pii, filters)
		sql_str = str(query)
		self.assertIn("ITEM-001", sql_str)
		self.assertIn("Products", sql_str)
