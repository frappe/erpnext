import frappe
from frappe.utils import add_days, nowdate

import erpnext
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.regional.report.uae_vat_201.uae_vat_201 import (
	execute,
	get_exempt_total,
	get_reverse_charge_recoverable_tax,
	get_reverse_charge_recoverable_total,
	get_reverse_charge_tax,
	get_reverse_charge_total,
	get_standard_rated_expenses_tax,
	get_standard_rated_expenses_total,
	get_total_emiratewise,
	get_tourist_tax_return_tax,
	get_tourist_tax_return_total,
	get_zero_rated_total,
)
from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse_account
from erpnext.tests.utils import ERPNextTestSuite


class TestUaeVat201(ERPNextTestSuite):
	def setUp(self):
		set_vat_accounts()

		make_customer()

		make_supplier()

		create_warehouse("_Test UAE VAT Supplier Warehouse", company="_Test Company UAE VAT")

		make_item("_Test UAE VAT Item", properties={"is_zero_rated": 0, "is_exempt": 0})
		make_item("_Test UAE VAT Zero Rated Item", properties={"is_zero_rated": 1, "is_exempt": 0})
		make_item("_Test UAE VAT Exempt Item", properties={"is_zero_rated": 0, "is_exempt": 1})

	def test_validate_company_region(self):
		self.assertRaises(
			frappe.exceptions.ValidationError,
			execute,
			{"company": "_Test Company"},
		)

	def test_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts User")

		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, execute, {"company": "_Test Company UAE VAT"})
		self.assertRaises(frappe.ValidationError, execute, {})

	def test_uae_vat_201_report(self):
		make_sales_invoices()
		create_purchase_invoices()

		filters = {"company": "_Test Company UAE VAT"}
		total_emiratewise = get_total_emiratewise(filters)
		amounts_by_emirate = {}
		for data in total_emiratewise:
			emirate, amount, vat = data
			amounts_by_emirate[emirate] = {
				"raw_amount": amount,
				"raw_vat_amount": vat,
			}
		self.assertEqual(amounts_by_emirate["Sharjah"]["raw_amount"], 100)
		self.assertEqual(amounts_by_emirate["Sharjah"]["raw_vat_amount"], 5)
		self.assertEqual(amounts_by_emirate["Dubai"]["raw_amount"], 200)
		self.assertEqual(amounts_by_emirate["Dubai"]["raw_vat_amount"], 10)
		self.assertEqual(get_tourist_tax_return_total(filters), 100)
		self.assertEqual(get_tourist_tax_return_tax(filters), 2)
		self.assertEqual(get_zero_rated_total(filters), 100)
		self.assertEqual(get_exempt_total(filters), 100)
		self.assertEqual(get_standard_rated_expenses_total(filters), 250)
		self.assertEqual(get_standard_rated_expenses_tax(filters), 1)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": True}
	)
	def test_uae_vat_201_report_with_foreign_transaction(self):
		pi = make_purchase_invoice(
			company="_Test Company UAE VAT",
			supplier="_Test UAE Supplier",
			supplier_warehouse="_Test UAE VAT Supplier Warehouse - _TCUV",
			warehouse="_Test UAE VAT Supplier Warehouse - _TCUV",
			currency="USD",
			conversion_rate=3.67,
			cost_center="Main - _TCUV",
			expense_account="Cost of Goods Sold - _TCUV",
			item="_Test UAE VAT Item",
			do_not_save=1,
			uom="Nos",
		)
		pi.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "VAT 5% - _TCUV",
				"cost_center": "Main - _TCUV",
				"description": "VAT 5% @ 5.0",
				"rate": 5.0,
			},
		)
		pi.recoverable_standard_rated_expenses = 50
		pi.save().submit()

		filters = {"company": "_Test Company UAE VAT"}
		self.assertEqual(get_standard_rated_expenses_total(filters), 917.5)
		self.assertEqual(get_standard_rated_expenses_tax(filters), 50)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": True}
	)
	def test_uae_vat_201_sales_vat_in_foreign_currency(self):
		"""VAT on a foreign currency invoice must be reported in company currency."""
		si = create_sales_invoice(
			company="_Test Company UAE VAT",
			customer="_Test UAE Customer",
			currency="USD",
			conversion_rate=3.67,
			rate=1000,
			qty=1,
			warehouse="Finished Goods - _TCUV",
			debit_to="Debtors - _TCUV",
			income_account="Sales - _TCUV",
			expense_account="Cost of Goods Sold - _TCUV",
			cost_center="Main - _TCUV",
			item="_Test UAE VAT Item",
			do_not_save=1,
		)
		si.vat_emirate = "Dubai"
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "VAT 5% - _TCUV",
				"cost_center": "Main - _TCUV",
				"description": "VAT 5% @ 5.0",
				"rate": 5.0,
			},
		)
		si.submit()

		filters = {"company": "_Test Company UAE VAT"}
		amounts_by_emirate = dict(
			(emirate, (amount, vat)) for emirate, amount, vat in get_total_emiratewise(filters)
		)
		amount, vat = amounts_by_emirate["Dubai"]

		self.assertEqual(amount, 3670)
		self.assertEqual(vat, 183.5)
		self.assertEqual(vat, si.taxes[0].base_tax_amount_after_discount_amount)
		self.assertNotEqual(vat, si.items[0].tax_amount)

	def test_uae_vat_201_mixed_invoice_excludes_exempt_and_zero_rated_vat(self):
		si = create_sales_invoice(
			company="_Test Company UAE VAT",
			customer="_Test UAE Customer",
			currency="AED",
			rate=100,
			qty=1,
			warehouse="Finished Goods - _TCUV",
			debit_to="Debtors - _TCUV",
			income_account="Sales - _TCUV",
			expense_account="Cost of Goods Sold - _TCUV",
			cost_center="Main - _TCUV",
			item="_Test UAE VAT Item",
			do_not_save=1,
		)
		si.vat_emirate = "Ajman"
		for item_code in ("_Test UAE VAT Zero Rated Item", "_Test UAE VAT Exempt Item"):
			si.append(
				"items",
				{
					"item_code": item_code,
					"qty": 1,
					"rate": 100,
					"warehouse": "Finished Goods - _TCUV",
					"income_account": "Sales - _TCUV",
					"expense_account": "Cost of Goods Sold - _TCUV",
					"cost_center": "Main - _TCUV",
				},
			)
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "VAT 5% - _TCUV",
				"cost_center": "Main - _TCUV",
				"description": "VAT 5% @ 5.0",
				"rate": 5.0,
			},
		)
		si.submit()

		# the single On Net Total row taxes all three items, so the invoice level figure is 15
		self.assertEqual(si.taxes[0].base_tax_amount_after_discount_amount, 15)

		filters = {"company": "_Test Company UAE VAT"}
		amounts_by_emirate = dict(
			(emirate, (amount, vat)) for emirate, amount, vat in get_total_emiratewise(filters)
		)
		amount, vat = amounts_by_emirate["Ajman"]

		# only the standard rated row belongs in box 1
		self.assertEqual(amount, 100)
		self.assertEqual(vat, 5)
		self.assertEqual(get_zero_rated_total(filters), 100)
		self.assertEqual(get_exempt_total(filters), 100)

	def test_uae_vat_201_reverse_charge_debit_note(self):
		frappe.flags.country = "United Arab Emirates"
		self.addCleanup(setattr, frappe.flags, "country", None)
		pi = make_uae_purchase_invoice(qty=10, rate=200)
		pi.reverse_charge = "Y"
		pi.recoverable_reverse_charge = 100
		pi.submit()

		debit_note = make_return_doc("Purchase Invoice", pi.name)
		debit_note.items[0].qty = -2
		debit_note.submit()

		filters = {"company": "_Test Company UAE VAT"}
		self.assertEqual(get_reverse_charge_total(filters), 1600)
		self.assertEqual(get_reverse_charge_tax(filters), 80)
		self.assertEqual(get_reverse_charge_recoverable_total(filters), 1600)
		self.assertEqual(get_reverse_charge_recoverable_tax(filters), 80)

	def test_uae_vat_201_returns_reduce_expenses_and_tourist_refunds(self):
		pi = make_uae_purchase_invoice(qty=10, rate=100)
		pi.recoverable_standard_rated_expenses = 50
		pi.submit()
		debit_note = make_return_doc("Purchase Invoice", pi.name)
		debit_note.items[0].qty = -2
		debit_note.recoverable_standard_rated_expenses = -10
		debit_note.submit()

		si = make_uae_sales_invoice("Dubai", qty=1, rate=600)
		si.tourist_tax_return = 25
		si.submit()
		credit_note = make_return_doc("Sales Invoice", si.name)
		credit_note.tourist_tax_return = -25
		credit_note.submit()

		filters = {"company": "_Test Company UAE VAT"}
		self.assertEqual(get_standard_rated_expenses_total(filters), 800)
		self.assertEqual(get_standard_rated_expenses_tax(filters), 40)
		self.assertEqual(get_tourist_tax_return_total(filters), 0)
		self.assertEqual(get_tourist_tax_return_tax(filters), 0)

	def test_uae_vat_201_supplies_without_emirate(self):
		make_uae_sales_invoice(None, qty=10, rate=40).submit()

		_columns, data = execute(
			{"company": "_Test Company UAE VAT", "from_date": nowdate(), "to_date": nowdate()}
		)
		row = next(row for row in data if row["legend"] == "Standard rated supplies with no VAT Emirate")
		self.assertEqual(row["amount"], frappe.format(400, "Currency"))
		self.assertEqual(row["vat_amount"], frappe.format(20, "Currency"))

	def test_uae_vat_201_standard_rated_expenses_exclude_lines_without_vat(self):
		pi = make_uae_purchase_invoice(qty=10, rate=100)
		pi.append("items", {**pi.items[0].as_dict(), "name": None, "qty": 5})
		pi.items[1].item_tax_template = make_zero_vat_template()
		pi.recoverable_standard_rated_expenses = 50
		pi.submit()

		self.assertEqual(pi.base_net_total, 1500)
		self.assertEqual(get_standard_rated_expenses_total({"company": "_Test Company UAE VAT"}), 1000)

	def test_uae_vat_201_to_date_without_from_date(self):
		create_purchase_invoices()

		filters = {"company": "_Test Company UAE VAT", "to_date": add_days(nowdate(), -1)}
		self.assertEqual(get_standard_rated_expenses_tax(filters), 0)
		filters["to_date"] = nowdate()
		self.assertEqual(get_standard_rated_expenses_tax(filters), 1)


def set_vat_accounts():
	if not frappe.db.exists("UAE VAT Settings", "_Test Company UAE VAT"):
		vat_accounts = frappe.get_all(
			"Account",
			fields=["name"],
			filters={"company": "_Test Company UAE VAT", "is_group": 0, "account_type": "Tax"},
		)

		uae_vat_accounts = []
		for account in vat_accounts:
			uae_vat_accounts.append({"doctype": "UAE VAT Account", "account": account.name})

		frappe.get_doc(
			{
				"company": "_Test Company UAE VAT",
				"uae_vat_accounts": uae_vat_accounts,
				"doctype": "UAE VAT Settings",
			}
		).insert()


def make_customer():
	if not frappe.db.exists("Customer", "_Test UAE Customer"):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test UAE Customer",
				"customer_type": "Company",
			}
		)
		customer.insert()


def make_supplier():
	if not frappe.db.exists("Supplier", "_Test UAE Supplier"):
		frappe.get_doc(
			{
				"supplier_group": "Local",
				"supplier_name": "_Test UAE Supplier",
				"supplier_type": "Individual",
				"doctype": "Supplier",
			}
		).insert()


def create_warehouse(warehouse_name, properties=None, company=None):
	if not company:
		company = "_Test Company"

	warehouse_id = erpnext.encode_company_abbr(warehouse_name, company)
	if not frappe.db.exists("Warehouse", warehouse_id):
		warehouse = frappe.new_doc("Warehouse")
		warehouse.warehouse_name = warehouse_name
		warehouse.parent_warehouse = "All Warehouses - _TCUV"
		warehouse.company = company
		warehouse.account = get_warehouse_account(warehouse_name, company)
		if properties:
			warehouse.update(properties)
		warehouse.save()
		return warehouse.name
	else:
		return warehouse_id


def make_zero_vat_template():
	title = "_Test UAE Zero VAT"
	name = frappe.db.get_value("Item Tax Template", {"title": title, "company": "_Test Company UAE VAT"})
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": title,
				"company": "_Test Company UAE VAT",
				"taxes": [{"tax_type": "VAT 5% - _TCUV", "tax_rate": 0}],
			}
		)
		.insert()
		.name
	)


def make_item(item_code, properties=None):
	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

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

	return item


def make_uae_sales_invoice(emirate, item="_Test UAE VAT Item", tax=True, **args):
	"""Returns an unsaved AED Sales Invoice of the UAE test company, with VAT 5% when `tax` is set."""
	si = create_sales_invoice(
		company="_Test Company UAE VAT",
		customer="_Test UAE Customer",
		currency="AED",
		warehouse="Finished Goods - _TCUV",
		debit_to="Debtors - _TCUV",
		income_account="Sales - _TCUV",
		expense_account="Cost of Goods Sold - _TCUV",
		cost_center="Main - _TCUV",
		item=item,
		do_not_save=1,
		**args,
	)
	si.vat_emirate = emirate
	if tax:
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "VAT 5% - _TCUV",
				"cost_center": "Main - _TCUV",
				"description": "VAT 5% @ 5.0",
				"rate": 5.0,
			},
		)
	return si


def make_sales_invoices():
	def make_sales_invoices_wrapper(emirate, item, tax=True, tourist_tax=False):
		si = make_uae_sales_invoice(emirate, item, tax)
		if tourist_tax:
			si.tourist_tax_return = 2
		si.submit()

	# Define Item Names
	uae_item = "_Test UAE VAT Item"
	uae_exempt_item = "_Test UAE VAT Exempt Item"
	uae_zero_rated_item = "_Test UAE VAT Zero Rated Item"

	# Sales Invoice with standard rated expense in Dubai
	make_sales_invoices_wrapper("Dubai", uae_item)
	# Sales Invoice with standard rated expense in Sharjah
	make_sales_invoices_wrapper("Sharjah", uae_item)
	# Sales Invoice with Tourist Tax Return
	make_sales_invoices_wrapper("Dubai", uae_item, True, True)
	# Sales Invoice with Exempt Item
	make_sales_invoices_wrapper("Sharjah", uae_exempt_item, False)
	# Sales Invoice with Zero Rated Item
	make_sales_invoices_wrapper("Sharjah", uae_zero_rated_item, False)


def create_purchase_invoices():
	pi = make_uae_purchase_invoice()
	pi.recoverable_standard_rated_expenses = 1
	pi.submit()


def make_uae_purchase_invoice(**args):
	"""Returns an unsaved AED Purchase Invoice of the UAE test company with VAT 5%."""
	pi = make_purchase_invoice(
		company="_Test Company UAE VAT",
		supplier="_Test UAE Supplier",
		supplier_warehouse="_Test UAE VAT Supplier Warehouse - _TCUV",
		warehouse="_Test UAE VAT Supplier Warehouse - _TCUV",
		currency="AED",
		cost_center="Main - _TCUV",
		expense_account="Cost of Goods Sold - _TCUV",
		item="_Test UAE VAT Item",
		do_not_save=1,
		uom="Nos",
		**args,
	)
	pi.append(
		"taxes",
		{
			"charge_type": "On Net Total",
			"account_head": "VAT 5% - _TCUV",
			"cost_center": "Main - _TCUV",
			"description": "VAT 5% @ 5.0",
			"rate": 5.0,
		},
	)
	return pi
