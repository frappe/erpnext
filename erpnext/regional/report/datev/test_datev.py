from __future__ import unicode_literals

import unittest
import json
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

class TestDatev(unittest.TestCase):
	def __init__(self):
		with open("test_records.json", "r") as test_records:
			make_test_objects("Account", json.load(test_records))

		self.filters = {
			'company': '_Test GmbH',
			'from_date': getdate(),
			'to_date': getdate(),
		}
		validate(filters)

	def _validate_keys(self, get_data, allowed_keys):
		"""
		Validate that the dict contains only allowed keys.
		
		Params:
		get_data -- Function that returns a list of dicts.
		allowed_keys -- List of allowed keys
		"""
		data = get_data(self.filters, as_dict=1)
		actual_set = set(data[0].keys())
		allowed_set = set(allowed_keys)
		self.assert(actual_set.issubset(allowed_set))

	def test_transaction(self):
		self._validate_keys(get_transactions, Transactions.COLUMNS)

	def test_customer(self):
		self._validate_keys(get_customers, DebtorsCreditors.COLUMNS)

	def test_supplier(self):
		self._validate_keys(get_suppliers, DebtorsCreditors.COLUMNS)

	def test_account_name(self):
		self._validate_keys(get_account_names, AccountNames.COLUMNS)

	def test_csv(self):
		download_datev_csv(self.filters)
		zipfile.is_zipfile(frappe.response['filecontent'])
