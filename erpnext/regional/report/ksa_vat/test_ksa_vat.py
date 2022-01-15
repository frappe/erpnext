# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest import TestCase

import frappe
from frappe.utils import add_months, nowdate

from erpnext.regional.report.ksa_vat.ksa_vat import get_data
from erpnext.regional.saudi_arabia.wizard.operations.setup_ksa_vat_setting import (
	create_ksa_vat_setting,
)


class TestKSAVAT(TestCase):
	def setUp(self):
		si = frappe.qb.DocType('Sales Invoice')
		frappe.qb.from_(si).delete().where(si.company == "_Test Company KSA VAT").run()

		# Enable purchase tests after https://github.com/frappe/erpnext/pull/29175 is merged
		# pi = frappe.qb.DocType('Purchase Invoice')
		# frappe.qb.from_(pi).delete().where(pi.company == "_Test Company KSA VAT").run()

		make_company("_Test Company KSA VAT", "_TCKV")
		if frappe.db.exists('KSA VAT Setting', "_Test Company KSA VAT") is None:
			create_ksa_vat_setting("_Test Company KSA VAT")

		make_customer()
		# make_supplier()

		make_item("_Test KSA VAT Item", properties={"is_zero_rated": 0, "is_exempt": 0})
		make_item("_Test KSA VAT Zero Rated Item", properties={"is_zero_rated": 1, "is_exempt": 0})
		make_item("_Test KSA VAT Exempt Item", properties={"is_zero_rated": 0, "is_exempt": 1})

		generate_sales_invoices()
		# generate_purchase_invoices()

	def test_ksa_vat_report(self):
		data = get_data({
			"company": "_Test Company KSA VAT",
			"from_date": add_months(nowdate(), -1),
			"to_date": nowdate(),
		})

		expected_data = [
			{
				"title": 'VAT on Sales',
				"amount": '',
				"adjustment_amount": '',
				"vat_amount": '',
				"currency": "SAR"
			},
			{
				"title": "Standard rated Sales",
				"amount": 2500.00,
				"adjustment_amount": -1000.00,
				"vat_amount": 75.00,
				"currency": "SAR"
			},
			{
				"title": "Zero rated domestic sales",
				"amount": 500.00,
				"adjustment_amount": -100.00,
				"vat_amount": 00.0,
				"currency": "SAR"
			},
			{
				"title": "Exempted sales",
				"amount": 1000.00,
				"adjustment_amount": -600.00,
				"vat_amount": 0.00,
				"currency": "SAR"
			},
			{
				"title": "Grand Total",
				"amount": 4000.00,
				"adjustment_amount": -1700.00,
				"vat_amount": 75.00,
				"currency": "SAR"
			},
		]

		self.assertEqual(expected_data[0], data[0])
		self.assertEqual(expected_data[1], data[1])
		self.assertEqual(expected_data[2], data[2])
		self.assertEqual(expected_data[3], data[3])
		self.assertEqual(expected_data[4], data[4])


def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": company_name,
			"abbr": abbr,
			"default_currency": "SAR",
			"country": "Saudi Arabia",
			"create_chart_of_accounts_based_on": "Standard Template",
		})
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.company_name_in_arabic = company_name
	company.tax_id = "1234567890"
	company.save()
	return company


def make_customer():
	if not frappe.db.exists("Customer", "_Test KSA Customer"):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test KSA Customer",
			"customer_type": "Company",
		})
		customer.insert()


def make_item(item_code, properties=None):
	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"description": item_code,
			"item_group": "Products"
		})

		if properties:
			item.update(properties)

		item.insert()


def generate_sales_invoices():
	# Create invoices
	create_sales_invoice(rate=500, qty=5, item_tax_template="KSA VAT 5% - _TCKV")
	create_sales_invoice(item_code="_Test KSA VAT Zero Rated Item", qty=5)
	create_sales_invoice(item_code="_Test KSA VAT Exempt Item", rate=200, qty=5)

	# Create returns
	create_sales_invoice(is_return=1, rate=500, qty=-2, item_tax_template="KSA VAT 5% - _TCKV")
	create_sales_invoice(is_return=1, item_code="_Test KSA VAT Zero Rated Item", qty=-1)
	create_sales_invoice(is_return=1, item_code="_Test KSA VAT Exempt Item", rate=200, qty=-3)


def create_sales_invoice(**args):
	si = frappe.new_doc("Sales Invoice")
	args = frappe._dict(args)
	if args.posting_date:
		si.set_posting_time = 1
	si.posting_date = args.posting_date or nowdate()

	si.company = args.company or "_Test Company KSA VAT"
	si.customer = args.customer or "_Test KSA Customer"
	si.debit_to = args.debit_to or "Debtors - _TCKV"
	si.update_stock = args.update_stock or 0
	si.is_pos = args.is_pos or 0
	si.is_return = args.is_return or 0
	si.return_against = args.return_against
	si.currency = args.currency or "SAR"
	si.conversion_rate = args.conversion_rate or 1
	si.naming_series = args.naming_series or "T-SINV-"
	si.cost_center = args.parent_cost_center

	si.append("items", {
		"item_code": args.item or args.item_code or "_Test KSA VAT Item",
		"item_name": args.item_name or "_Test KSA VAT Item",
		"description": args.description or "_Test KSA VAT Item",
		"is_zero_rated": args.is_zero_rated or 0,
		"is_exempt": args.is_exempt or 0,
		"warehouse": args.warehouse or "Stores - _TCKV",
		"qty": args.qty or 1,
		"uom": args.uom or "Nos",
		"stock_uom": args.uom or "Nos",
		"rate": args.rate if args.get("rate") is not None else 100,
		"price_list_rate": args.price_list_rate if args.get("price_list_rate") is not None else 100,
		"item_tax_template": args.item_tax_template or None,
		"income_account": args.income_account or "Sales - _TCKV",
		"expense_account": args.expense_account or "Cost of Goods Sold - _TCKV",
		"discount_account": args.discount_account or None,
		"discount_amount": args.discount_amount or 0,
		"asset": args.asset or None,
		"cost_center": args.cost_center or "Main - _TCKV",
		"serial_no": args.serial_no or None,
		"conversion_factor": 1,
		"incoming_rate": args.incoming_rate or 0
	})

	si.append("taxes", {
		"charge_type": "On Net Total",
		"account_head": "VAT 5% - _TCKV",
		"cost_center": "Main - _TCKV",
		"description": "VAT 5% @ 5.0",
		"rate": 0.00
	})

	if not args.do_not_save:
		si.insert()
		if not args.do_not_submit:
			si.submit()
		else:
			si.payment_schedule = []
	else:
		si.payment_schedule = []

	return si
