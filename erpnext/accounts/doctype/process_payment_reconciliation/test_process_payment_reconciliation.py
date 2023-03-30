# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase


class TestProcessPaymentReconciliation(unittest.TestCase):
	# class TestProcessPaymentReconciliation(FrappeTestCase):
	def setUp(self):
		self.test_records = frappe.get_test_records("Process Payment Reconciliation")
		self.create_company()
		self.clear_old_records()
		self.create_new_records()

	def tearDown(self):
		pass

	def create_company(self):
		company = None
		name = "Test Process PR"
		if frappe.db.exists("Company", name):
			company = frappe.get_doc("Company", name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "All Warehouses - TPP"
		self.income_account = "Sales - TPP"
		self.expense_account = "Cost of Goods Sold - TPP"
		self.debit_to = "Debtors - TPP"
		self.creditors = "Creditors - TPP"

	def clear_old_records(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def create_new_records(self):
		for x in range(4):
			si = frappe.copy_doc(self.test_records[0])  # template for Sales Invoice
			si.save().submit()

		for x in range(2):
			pe = frappe.copy_doc(self.test_records[1])  # template for Payment Entry
			pe.save().submit()

	def test_01_dummy(self):
		pass
