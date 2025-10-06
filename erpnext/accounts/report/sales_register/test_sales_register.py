import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.sales_register.sales_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestItemWiseSalesRegister(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.create_child_cost_center()

	def tearDown(self):
		frappe.db.rollback()

	def create_child_cost_center(self):
		cc_name = "South Wing"
		if frappe.db.exists("Cost Center", cc_name):
			cc = frappe.get_doc("Cost Center", cc_name)
		else:
			parent = frappe.db.get_value("Cost Center", self.cost_center, "parent_cost_center")
			cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"company": self.company,
					"is_group": False,
					"parent_cost_center": parent,
					"cost_center_name": cc_name,
				}
			)
			cc = cc.save()
		self.south_cc = cc.name

	def create_sales_invoice(self, rate=100, do_not_submit=False):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=rate,
			price_list_rate=rate,
			do_not_save=1,
		)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def test_basic_report_output(self):
		si = self.create_sales_invoice(rate=98)

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"voucher_type": si.doctype,
			"voucher_no": si.name,
			"posting_date": getdate(),
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 98.0,
			"grand_total": 98.0,
			"debit": 98.0,
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_journal_with_cost_center_filter(self):
		je1 = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(),
				"accounts": [
					{
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"credit_in_account_currency": 77,
						"credit": 77,
						"is_advance": "Yes",
						"cost_center": self.cost_center,
					},
					{
						"account": self.cash,
						"debit_in_account_currency": 77,
						"debit": 77,
					},
				],
			}
		)
		je1.submit()

		je2 = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(),
				"accounts": [
					{
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"credit_in_account_currency": 98,
						"credit": 98,
						"is_advance": "Yes",
						"cost_center": self.south_cc,
					},
					{
						"account": self.cash,
						"debit_in_account_currency": 98,
						"debit": 98,
					},
				],
			}
		)
		je2.submit()

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"include_payments": True,
				"customer": self.customer,
				"cost_center": self.cost_center,
			}
		)
		report_output = execute(filters)[1]
		filtered_output = [x for x in report_output if x.get("voucher_no") == je1.name]
		self.assertEqual(len(filtered_output), 1)
		expected_result = {
			"voucher_type": je1.doctype,
			"voucher_no": je1.name,
			"posting_date": je1.posting_date,
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 77.0,
			"credit": 77.0,
		}
		result_fields = {k: v for k, v in filtered_output[0].items() if k in expected_result}
		self.assertDictEqual(result_fields, expected_result)

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"include_payments": True,
				"customer": self.customer,
				"cost_center": self.south_cc,
			}
		)
		report_output = execute(filters)[1]
		filtered_output = [x for x in report_output if x.get("voucher_no") == je2.name]
		self.assertEqual(len(filtered_output), 1)
		expected_result = {
			"voucher_type": je2.doctype,
			"voucher_no": je2.name,
			"posting_date": je2.posting_date,
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 98.0,
			"credit": 98.0,
		}
		result_output = {k: v for k, v in filtered_output[0].items() if k in expected_result}
		self.assertDictEqual(result_output, expected_result)
