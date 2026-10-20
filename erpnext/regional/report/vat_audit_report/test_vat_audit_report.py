# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.regional.report.vat_audit_report.vat_audit_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestVATAuditReport(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company SA VAT"

		create_account(
			account_name="VAT - 0%",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCSV",
			company="_Test Company SA VAT",
		)
		create_account(
			account_name="VAT - 15%",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCSV",
			company="_Test Company SA VAT",
		)
		set_sa_vat_accounts()

		make_item("_Test SA VAT Item")
		make_item("_Test SA VAT Zero Rated Item", properties={"is_zero_rated": 1})

		make_customer()
		make_supplier()

		make_sales_invoices()
		create_purchase_invoices()

	def test_vat_audit_report(self):
		filters = {"company": "_Test Company SA VAT", "from_date": today(), "to_date": today()}
		columns, data = execute(filters)
		total_tax_amount = 0
		total_row_tax = 0
		for row in data:
			keys = row.keys()
			# skips total row tax_amount in if.. and skips section header in elif..
			if "voucher_no" in keys:
				total_tax_amount = total_tax_amount + row["tax_amount"]
			elif "tax_amount" in keys:
				total_row_tax = total_row_tax + row["tax_amount"]

		self.assertEqual(total_tax_amount, total_row_tax)

	def test_user_permissions(self):
		other_customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "_Test SA Customer " + frappe.generate_hash(length=6)}
		).insert()
		permitted_invoice = make_sa_sales_invoice("_Test SA VAT Item", 200.0)
		other_invoice = make_sa_sales_invoice("_Test SA VAT Item", 200.0, customer=other_customer.name)
		for invoice in (permitted_invoice, other_invoice):
			invoice.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": "VAT - 15% - _TCSV",
					"cost_center": "Main - _TCSV",
					"description": "VAT 15%",
					"rate": 15,
				},
			)
			invoice.submit()

		user = frappe.get_doc(
			{"doctype": "User", "email": "test-sa-vat-audit@example.com", "first_name": "SA VAT Audit"}
		).insert()
		user.add_roles("Accounts User")
		user = user.name
		frappe.permissions.add_user_permission("Customer", "_Test SA Customer", user)
		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		with self.set_user(user):
			voucher_nos = [row.get("voucher_no") for row in execute(filters)[1]]
		self.assertIn(permitted_invoice.name, voucher_nos)
		self.assertNotIn(other_invoice.name, voucher_nos)

		frappe.permissions.add_user_permission("Company", "_Test Company", user)
		with self.set_user(user):
			self.assertRaises(frappe.PermissionError, execute, filters)

	def test_vat_charged_as_actual_amount(self):
		si = make_sa_sales_invoice("_Test SA VAT Item", 500.0)
		si.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "VAT - 15% - _TCSV",
				"cost_center": "Main - _TCSV",
				"description": "VAT 15%",
				"tax_amount": 75,
			},
		)
		si.submit()

		filters = {"company": self.company, "from_date": today(), "to_date": today()}
		row = next(row for row in execute(filters)[1] if row.get("voucher_no") == si.name)
		self.assertEqual((row["net_amount"], row["tax_amount"]), (500, 75))

	def test_actual_vat_is_one_rate_per_invoice(self):
		make_item("_Test SA VAT Item 2")
		si = make_sa_sales_invoice("_Test SA VAT Item", 500.0)
		si.append(
			"items", {**si.items[0].as_dict(), "name": None, "item_code": "_Test SA VAT Item 2", "rate": 0.99}
		)
		si.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "VAT - 15% - _TCSV",
				"cost_center": "Main - _TCSV",
				"description": "VAT 15%",
				"tax_amount": 75.15,
			},
		)
		si.submit()

		filters = {"company": self.company, "from_date": today(), "to_date": today()}
		rows = [row for row in execute(filters)[1] if row.get("voucher_no") == si.name]
		self.assertEqual(len(rows), 1)
		self.assertEqual((rows[0]["net_amount"], rows[0]["tax_amount"]), (500.99, 75.15))

	def test_reverse_charge_shows_input_and_output_vat(self):
		pi = self.make_reverse_charge_purchase()
		self.assertEqual(self.get_figures(pi), [(1000, -150, 850), (1000, 150, 1150)])

		# item tax details migrated from the old JSON field keep a Deduct row's taxable amount positive
		deduct_tax_row = next(tax.name for tax in pi.taxes if tax.add_deduct_tax == "Deduct")
		frappe.db.set_value(
			"Item Wise Tax Detail", {"parent": pi.name, "tax_row": deduct_tax_row}, "taxable_amount", 1000
		)
		self.assertEqual(self.get_figures(pi), [(1000, -150, 850), (1000, 150, 1150)])

	def test_reverse_charge_return_stays_negative(self):
		debit_note = self.make_reverse_charge_purchase(is_return=1)
		self.assertEqual(self.get_figures(debit_note), [(-1000, -150, -1150), (-1000, 150, -850)])

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_negative_rates_for_items": 1})
	def test_reverse_charge_credit_line_reduces_supplies(self):
		pi = self.make_reverse_charge_purchase(credit_amount=100)
		self.assertEqual(self.get_figures(pi), [(900, -135, 765), (900, 135, 1035)])

	def make_reverse_charge_purchase(self, is_return: int = 0, credit_amount: float = 0):
		output_vat_account = create_account(
			account_name="VAT Reverse Charge",
			account_type="Tax",
			parent_account="Duties and Taxes - _TCSV",
			company=self.company,
		)
		settings = frappe.get_doc("South Africa VAT Settings", self.company)
		if output_vat_account not in [row.account for row in settings.vat_accounts]:
			settings.append("vat_accounts", {"account": output_vat_account})
			settings.save()

		pi = make_sa_purchase_invoice(1000, qty=-1 if is_return else 1, is_return=is_return)
		if credit_amount:
			make_item("_Test SA VAT Item 2")
			pi.append(
				"items",
				{
					**pi.items[0].as_dict(),
					"name": None,
					"item_code": "_Test SA VAT Item 2",
					"rate": -credit_amount,
				},
			)
		for account, add_deduct_tax in (("VAT - 15% - _TCSV", "Add"), (output_vat_account, "Deduct")):
			pi.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"category": "Total",
					"add_deduct_tax": add_deduct_tax,
					"account_head": account,
					"cost_center": "Main - _TCSV",
					"description": "VAT 15%",
					"rate": 15,
				},
			)
		pi.submit()
		return pi

	def get_figures(self, invoice):
		filters = {"company": self.company, "from_date": today(), "to_date": today()}
		rows = [row for row in execute(filters)[1] if row.get("voucher_no") == invoice.name]
		return sorted((row["net_amount"], row["tax_amount"], row["gross_amount"]) for row in rows)


def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"default_currency": "ZAR",
				"country": "South Africa",
				"create_chart_of_accounts_based_on": "Standard Template",
			}
		)
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.save()

	return company


def set_sa_vat_accounts():
	if not frappe.db.exists("South Africa VAT Settings", "_Test Company SA VAT"):
		vat_accounts = frappe.get_all(
			"Account",
			fields=["name"],
			filters={"company": "_Test Company SA VAT", "is_group": 0, "account_type": "Tax"},
		)

		sa_vat_accounts = []
		for account in vat_accounts:
			sa_vat_accounts.append({"doctype": "South Africa VAT Account", "account": account.name})

		frappe.get_doc(
			{
				"company": "_Test Company SA VAT",
				"vat_accounts": sa_vat_accounts,
				"doctype": "South Africa VAT Settings",
			}
		).insert()


def make_customer():
	if not frappe.db.exists("Customer", "_Test SA Customer"):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test SA Customer",
				"customer_type": "Company",
			}
		).insert()


def make_supplier():
	if not frappe.db.exists("Supplier", "_Test SA Supplier"):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test SA Supplier",
				"supplier_type": "Company",
				"supplier_group": "All Supplier Groups",
			}
		).insert()


def make_item(item_code, properties=None):
	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"description": item_code,
				"item_group": "Products",
			}
		)

		if properties:
			item.update(properties)

		item.insert()


def make_sa_sales_invoice(item, rate, customer="_Test SA Customer"):
	return create_sales_invoice(
		company="_Test Company SA VAT",
		customer=customer,
		currency="ZAR",
		item=item,
		rate=rate,
		warehouse="Finished Goods - _TCSV",
		debit_to="Debtors - _TCSV",
		income_account="Sales - _TCSV",
		expense_account="Cost of Goods Sold - _TCSV",
		cost_center="Main - _TCSV",
		do_not_save=1,
	)


def make_sales_invoices():
	def make_sales_invoices_wrapper(item, rate, tax_account, tax_rate, tax=True):
		si = make_sa_sales_invoice(item, rate)
		if tax:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax_account,
					"cost_center": "Main - _TCSV",
					"description": "VAT 15% @ 15.0",
					"rate": tax_rate,
				},
			)

		si.submit()

	test_item = "_Test SA VAT Item"
	test_zero_rated_item = "_Test SA VAT Zero Rated Item"

	make_sales_invoices_wrapper(test_item, 100.0, "VAT - 15% - _TCSV", 15.0)
	make_sales_invoices_wrapper(test_zero_rated_item, 100.0, "VAT - 0% - _TCSV", 0.0)


def make_sa_purchase_invoice(rate, qty=1, is_return=0):
	return make_purchase_invoice(
		company="_Test Company SA VAT",
		supplier="_Test SA Supplier",
		supplier_warehouse="Finished Goods - _TCSV",
		warehouse="Finished Goods - _TCSV",
		currency="ZAR",
		cost_center="Main - _TCSV",
		expense_account="Cost of Goods Sold - _TCSV",
		item="_Test SA VAT Item",
		qty=qty,
		rate=rate,
		is_return=is_return,
		uom="Nos",
		do_not_save=1,
	)


def create_purchase_invoices():
	pi = make_sa_purchase_invoice(100)
	pi.append(
		"taxes",
		{
			"charge_type": "On Net Total",
			"account_head": "VAT - 15% - _TCSV",
			"cost_center": "Main - _TCSV",
			"description": "VAT 15% @ 15.0",
			"rate": 15.0,
		},
	)

	pi.submit()
