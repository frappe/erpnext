# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe import ValidationError
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.bank.test_bank import create_bank


class TestBankAccount(IntegrationTestCase):
	pass


def create_bank_account(**kwargs):
	filters = {
		"account_name": kwargs.get("account_name", "_Test Bank Account"),
		"bank": kwargs.get("bank", create_bank()),
	}

	bank_acc_doc = None
	if bank_account := frappe.db.exists("Bank Account", filters):
		bank_acc_doc = frappe.get_doc("Bank Account", bank_account)
	else:
		bank_acc_doc = frappe.new_doc("Bank Account")
		bank_acc_doc.update(filters)
		bank_acc_doc.branch_code = kwargs.get("branch_code", "TEST0123456")
		bank_acc_doc.bank_account_no = kwargs.get("bank_account_no", "5648972310")
		bank_acc_doc.is_default = kwargs.get("is_default", 0)
		if kwargs.get("is_company_account"):
			company = kwargs.get("company", "_Test Company")
			bank_acc_doc.company = company
			account = kwargs.get("account")
			if not account:
				abbr = frappe.db.get_value("Company", company, "abbr")
				account = create_account(
					company=company,
					account_name="_Test Account",
					account_type="Bank",
					account_currency="INR",
					parent_account=f"Bank Accounts - {abbr}",
				)
			bank_acc_doc.account = account
		else:
			bank_acc_doc.party_type = kwargs.get("party_type")
			bank_acc_doc.party = kwargs.get("party")

		bank_acc_doc.insert(ignore_mandatory=True)

	if kwargs.get("return_doc"):
		return bank_acc_doc

	return bank_acc_doc.name
