import frappe
from frappe.utils import getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWiseSalesRegister(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def create_sales_invoice(self, item=None, taxes=None, do_not_submit=False):
		si = create_sales_invoice(
			item=item or self.item,
			item_name=item or self.item,
			description=item or self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_save=1,
		)

		for tax in taxes or []:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax["account_head"],
					"cost_center": self.cost_center,
					"description": tax["description"],
					"rate": tax["rate"],
				},
			)

		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def test_basic_report_output(self):
		si = self.create_sales_invoice()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"item_code": si.items[0].item_code,
			"invoice": si.name,
			"posting_date": getdate(),
			"customer": si.customer,
			"debit_to": si.debit_to,
			"company": self.company,
			"income_account": si.items[0].income_account,
			"stock_qty": 1.0,
			"stock_uom": si.items[0].stock_uom,
			"rate": 100.0,
			"amount": 100.0,
			"total_tax": 0,
			"total_other_charges": 0,
			"total": 100.0,
			"currency": "INR",
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_grouped_report_handles_different_tax_descriptions(self):
		self.create_item(
			item_name="_Test Item Tax Description A", company="_Test Company", warehouse="Stores - _TC"
		)
		first_item = self.item
		self.create_item(
			item_name="_Test Item Tax Description B", company="_Test Company", warehouse="Stores - _TC"
		)
		second_item = self.item

		first_tax_description = "Tax Description A"
		second_tax_description = "Tax Description B"
		first_tax_amount_field = f"{frappe.scrub(first_tax_description)}_amount"
		second_tax_amount_field = f"{frappe.scrub(second_tax_description)}_amount"

		self.create_sales_invoice(
			item=first_item,
			taxes=[
				{
					"account_head": "_Test Account VAT - _TC",
					"description": first_tax_description,
					"rate": 5,
				}
			],
		)
		self.create_sales_invoice(
			item=second_item,
			taxes=[
				{
					"account_head": "_Test Account Service Tax - _TC",
					"description": second_tax_description,
					"rate": 2,
				}
			],
		)

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"group_by": "Customer",
			}
		)
		_, data, _, _, _, _ = execute(filters)

		grand_total_row = next(row for row in data if row.get("bold") and row.get("item_code") == "Total")

		self.assertEqual(grand_total_row[first_tax_amount_field], 5.0)
		self.assertEqual(grand_total_row[second_tax_amount_field], 2.0)
