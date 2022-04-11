# coding=utf-8

import zipfile
from unittest import TestCase

import frappe
from frappe.utils import cstr, now_datetime, today
from six import BytesIO

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.regional.germany.utils.datev.datev_constants import (
	AccountNames,
	DebtorsCreditors,
	Transactions,
)
from erpnext.regional.germany.utils.datev.datev_csv import get_datev_csv, get_header
from erpnext.regional.report.datev.datev import (
	download_datev_csv,
	get_account_names,
	get_customers,
	get_suppliers,
	get_transactions,
)


def make_company(company_name, abbr):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"default_currency": "EUR",
				"country": "Germany",
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "SKR04 mit Kontonummern",
			}
		)
		company.insert()
	else:
		company = frappe.get_doc("Company", company_name)

	# indempotent
	company.create_default_warehouses()

	if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": company.name}):
		company.create_default_cost_center()

	company.save()
	return company


def setup_fiscal_year():
	fiscal_year = None
	year = cstr(now_datetime().year)
	if not frappe.db.get_value("Fiscal Year", {"year": year}, "name"):
		try:
			fiscal_year = frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": year,
					"year_start_date": "{0}-01-01".format(year),
					"year_end_date": "{0}-12-31".format(year),
				}
			)
			fiscal_year.insert()
		except frappe.NameError:
			pass

	if fiscal_year:
		fiscal_year.set_as_default()


def make_customer_with_account(customer_name, company):
	acc_name = frappe.db.get_value(
		"Account", {"account_name": customer_name, "company": company.name}, "name"
	)

	if not acc_name:
		acc = frappe.get_doc(
			{
				"doctype": "Account",
				"parent_account": "1 - Forderungen aus Lieferungen und Leistungen - _TG",
				"account_name": customer_name,
				"company": company.name,
				"account_type": "Receivable",
				"account_number": "10001",
			}
		)
		acc.insert()
		acc_name = acc.name

	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Company",
				"accounts": [{"company": company.name, "account": acc_name}],
			}
		)
		customer.insert()
	else:
		customer = frappe.get_doc("Customer", customer_name)

	return customer


def make_item(item_code, company):
	warehouse_name = frappe.db.get_value(
		"Warehouse", {"warehouse_name": "Stores", "company": company.name}, "name"
	)

	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"description": item_code,
				"item_group": "All Item Groups",
				"is_stock_item": 0,
				"is_purchase_item": 0,
				"is_customer_provided_item": 0,
				"item_defaults": [{"default_warehouse": warehouse_name, "company": company.name}],
			}
		)
		item.insert()
	else:
		item = frappe.get_doc("Item", item_code)
	return item


def make_datev_settings(company):
	if not frappe.db.exists("DATEV Settings", company.name):
		frappe.get_doc(
			{
				"doctype": "DATEV Settings",
				"client": company.name,
				"client_number": "12345",
				"consultant_number": "67890",
				"temporary_against_account_number": "9999",
			}
		).insert()


class TestDatev(TestCase):
	def setUp(self):
		self.company = make_company("_Test GmbH", "_TG")
		self.customer = make_customer_with_account("_Test Kunde GmbH", self.company)
		self.filters = {
			"company": self.company.name,
			"from_date": today(),
			"to_date": today(),
			"temporary_against_account_number": "9999",
		}

		make_datev_settings(self.company)
		item = make_item("_Test Item", self.company)
		setup_fiscal_year()

		warehouse = frappe.db.get_value(
			"Item Default", {"parent": item.name, "company": self.company.name}, "default_warehouse"
		)

		income_account = frappe.db.get_value(
			"Account", {"account_number": "4200", "company": self.company.name}, "name"
		)

		tax_account = frappe.db.get_value(
			"Account", {"account_number": "3806", "company": self.company.name}, "name"
		)

		si = create_sales_invoice(
			company=self.company.name,
			customer=self.customer.name,
			currency=self.company.default_currency,
			debit_to=self.customer.accounts[0].account,
			income_account="4200 - Erlöse - _TG",
			expense_account="6990 - Herstellungskosten - _TG",
			cost_center=self.company.cost_center,
			warehouse=warehouse,
			item=item.name,
			do_not_save=1,
		)

		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": tax_account,
				"description": "Umsatzsteuer 19 %",
				"rate": 19,
				"cost_center": self.company.cost_center,
			},
		)

		si.cost_center = self.company.cost_center

		si.save()
		si.submit()

	def test_columns(self):
		def is_subset(get_data, allowed_keys):
			"""
			Validate that the dict contains only allowed keys.

			Params:
			get_data -- Function that returns a list of dicts.
			allowed_keys -- List of allowed keys
			"""
			data = get_data(self.filters)
			if data == []:
				# No data and, therefore, no columns is okay
				return True
			actual_set = set(data[0].keys())
			# allowed set must be interpreted as unicode to match the actual set
			allowed_set = set({frappe.as_unicode(key) for key in allowed_keys})
			return actual_set.issubset(allowed_set)

		self.assertTrue(is_subset(get_transactions, Transactions.COLUMNS))
		self.assertTrue(is_subset(get_customers, DebtorsCreditors.COLUMNS))
		self.assertTrue(is_subset(get_suppliers, DebtorsCreditors.COLUMNS))
		self.assertTrue(is_subset(get_account_names, AccountNames.COLUMNS))

	def test_header(self):
		self.assertTrue(Transactions.DATA_CATEGORY in get_header(self.filters, Transactions))
		self.assertTrue(AccountNames.DATA_CATEGORY in get_header(self.filters, AccountNames))
		self.assertTrue(DebtorsCreditors.DATA_CATEGORY in get_header(self.filters, DebtorsCreditors))

	def test_csv(self):
		test_data = [
			{
				"Umsatz (ohne Soll/Haben-Kz)": 100,
				"Soll/Haben-Kennzeichen": "H",
				"Kontonummer": "4200",
				"Gegenkonto (ohne BU-Schlüssel)": "10000",
				"Belegdatum": today(),
				"Buchungstext": "No remark",
				"Beleginfo - Art 1": "Sales Invoice",
				"Beleginfo - Inhalt 1": "SINV-0001",
			}
		]
		get_datev_csv(data=test_data, filters=self.filters, csv_class=Transactions)

	def test_download(self):
		"""Assert that the returned file is a ZIP file."""
		download_datev_csv(self.filters)

		# zipfile.is_zipfile() expects a file-like object
		zip_buffer = BytesIO()
		zip_buffer.write(frappe.response["filecontent"])

		self.assertTrue(zipfile.is_zipfile(zip_buffer))
