import frappe
import unittest
from erpnext.regional.germany.accounts_controller import validate_regional


class TestAccountsController(unittest.TestCase):

	def setUp(self):
		self.sales_invoice = frappe.get_last_doc('Sales Invoice')

	def test_validate_regional(self):
		validate_regional(self.sales_invoice)
