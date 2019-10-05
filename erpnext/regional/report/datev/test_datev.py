from __future__ import unicode_literals

import json
from unittest import TestCase
import frappe
from frappe.utils import getdate
from frappe.test_runner import make_test_objects
from erpnext.regional.report.datev.datev import validate
from erpnext.regional.report.datev.datev import get_transactions
from erpnext.regional.report.datev.datev import get_customers
from erpnext.regional.report.datev.datev import get_suppliers
from erpnext.regional.report.datev.datev import get_account_names
from erpnext.regional.report.datev.datev import get_datev_csv
from erpnext.regional.report.datev.datev import get_header
from erpnext.regional.report.datev.datev import download_datev_csv
from datev_constants import DataCategory
from datev_constants import Transactions
from datev_constants import DebtorsCreditors
from datev_constants import AccountNames
from datev_constants import QUERY_REPORT_COLUMNS
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

class TestDatev(TestCase):
	def setUp(self):
		with open("test_records.json", "r") as test_records:
			make_test_objects("Account", json.load(test_records))

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

	def test_csv(self):
		download_datev_csv(self.filters)
		zipfile.is_zipfile(frappe.response['filecontent'])
