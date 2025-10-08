from datetime import date

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.sales_invoice_trends.sales_invoice_trends import execute


class TestSalesInvoiceTrends(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_fiscal_year()
		self.create_customer()
		self.create_sales_invoice()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company_name = "_Test Sales Invoice Trends"
		abbr = "_SIT"
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "Stores - " + abbr
		self.finished_warehouse = "Finished Goods - " + abbr
		self.income_account = "Sales - " + abbr
		self.expense_account = "Cost of Goods Sold - " + abbr
		self.debit_to = "Debtors - " + abbr
		self.creditors = "Creditors - " + abbr

	def create_customer(self):
		name = "_Test SIT Customer"
		if frappe.db.exists("Customer", name):
			self.customer = name
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_fiscal_year(self):
		company = self.company
		today = date.today()

		existing_fy = frappe.get_all(
			"Fiscal Year",
			fields=["name", "year_start_date", "year_end_date"],
		)

		for fy in existing_fy:
			if fy.year_start_date <= today <= fy.year_end_date:
				fy_doc = frappe.get_doc("Fiscal Year", fy.name)

				if not any(c.company == company for c in fy_doc.companies):
					fy_doc.append("companies", {"company": company})
					fy_doc.save()

				return fy_doc.name

		if today.month >= 4:
			start_date = date(today.year, 4, 1)
			end_date = date(today.year + 1, 3, 31)
		else:
			start_date = date(today.year - 1, 4, 1)
			end_date = date(today.year, 3, 31)

		fy_doc = frappe.new_doc("Fiscal Year")
		fy_doc.year = f"FY-{start_date.year}-{end_date.year}"
		fy_doc.year_start_date = start_date
		fy_doc.year_end_date = end_date
		fy_doc.append("companies", {"company": company})
		fy_doc.insert()
		fy_doc.submit()

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=None, do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		if posting_date is None:
			posting_date = nowdate()

		sinv = create_sales_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.customer,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
		)
		sinv.submit()

		return sinv

	def clear_old_entries(self):
		doctype_list = [
			"Sales Invoice",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def test_invoice_with_filter_TC_ACC_532(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import get_active_fiscal_year

		filters = frappe._dict(
			company=self.company, based_on="Customer", period="Monthly", fiscal_year=get_active_fiscal_year()
		)

		columns, data = execute(filters=filters)

		self.assertIn("Customer:Link/Customer:120", columns)
		self.assertIn("Total(Qty):Float:120", columns)
		self.assertIn("Total(Amt):Currency:120", columns)

		self.assertTrue(len(data) > 0)

		first_row = data[0]
		self.assertEqual(first_row[0], "_Test SIT Customer")
		self.assertEqual(first_row[1], "All Territories")

		self.assertEqual(first_row[-2], 13.0)
		self.assertEqual(first_row[-1], 1300.0)
