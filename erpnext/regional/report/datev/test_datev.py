# coding=utf-8
from __future__ import unicode_literals

import os
import json
from unittest import TestCase
import frappe
from frappe.utils import getdate, today
from frappe.test_runner import make_test_objects
from erpnext.regional.report.datev.datev import validate
from erpnext.regional.report.datev.datev import get_transactions
from erpnext.regional.report.datev.datev import get_customers
from erpnext.regional.report.datev.datev import get_suppliers
from erpnext.regional.report.datev.datev import get_account_names
from erpnext.regional.report.datev.datev import get_datev_csv
from erpnext.regional.report.datev.datev import get_header
from erpnext.regional.report.datev.datev import download_datev_csv
from .datev_constants import DataCategory
from .datev_constants import Transactions
from .datev_constants import DebtorsCreditors
from .datev_constants import AccountNames
from .datev_constants import QUERY_REPORT_COLUMNS
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts

class TestDatev(TestCase):
	def setUp(self):
		self.company = "_Test GmbH"
		self.filters = {
			"company": self.company,
			"from_date": today(),
			"to_date": today()
		}
		test_records_path = os.path.join(os.path.dirname(__file__), "test_records.json")
		test_coa_path = os.path.join(os.path.dirname(__file__), "test_coa.json")

		with open(test_records_path, "r") as test_records_file:
			make_test_objects("Account", json.load(test_records_file))

		with open(test_coa_path, "r") as test_coa_file:
			test_coa = json.load(test_coa_file)
			create_charts(self.company, None, None, test_coa)
		
		customer = frappe.get_doc("Customer", "_Test Kunde GmbH")
		customer.append("accounts", {
			"company": self.company, 
			"account": "10001 - _Test Kunde GmbH - _TG"
		})
		customer.save()

		si = create_sales_invoice(
			company=self.company,
			customer="_Test Kunde GmbH",
			currency="EUR",
			debit_to="10001 - _Test Kunde GmbH - _TG",
			income_account="4200 - Erlöse - _TG",
			total=100
		)

		si.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "3806 - Umsatzsteuer 19% - _TG",
			"rate": 19
		})
		si.submit()

	def test_columns(self):
		def is_subset(get_data, allowed_keys):
			"""
			Validate that the dict contains only allowed keys.
			
			Params:
			get_data -- Function that returns a list of dicts.
			allowed_keys -- List of allowed keys
			"""
			data = get_data({
				'company': '_Test GmbH',
				'from_date': getdate(),
				'to_date': getdate(),
			}, as_dict=1)
			actual_set = set(data[0].keys())
			allowed_set = set(allowed_keys)
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
		test_data = [{
			"Umsatz (ohne Soll/Haben-Kz)": 100,
			"Soll/Haben-Kennzeichen": "H",
			"Kontonummer": "4200",
			"Gegenkonto (ohne BU-Schlüssel)": "10000",
			"Belegdatum": today(),
			"Buchungstext": "No remark",
			"Beleginfo - Art 1": "Sales Invoice",
			"Beleginfo - Inhalt 1": "SINV-0001"
		}]
		get_datev_csv(data=test_data, filters=self.filters, csv_class=Transactions)

	def test_download(self):
		download_datev_csv(self.filters)
		zipfile.is_zipfile(frappe.response['filecontent'])
