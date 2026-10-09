# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

<<<<<<< HEAD
test_ignore = ["Price List"]


import frappe

test_records = frappe.get_test_records("Customer Group")
=======
import frappe

from erpnext.accounts.party import DuplicatePartyAccountError
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomerGroup(ERPNextTestSuite):
	def test_invalid_party_accounts(self):
		group = frappe.new_doc("Customer Group")
		group.customer_group_name = "_Test Invalid Group Accounts"
		group.is_group = 0
		group.append("accounts", {"company": "_Test Company", "account": "Creditors - _TC"})
		with self.assertRaises(frappe.ValidationError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Accounts Receivable - _TC"})
		with self.assertRaises(frappe.ValidationError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		with self.assertRaises(DuplicatePartyAccountError):
			group.insert()

		group.accounts = []
		group.append("accounts", {"company": "_Test Company", "account": "Debtors - _TC"})
		group.insert()
>>>>>>> 981737c (fix(customer group): validate party accounts before saving)
