# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestModeofPayment(IntegrationTestCase):
	pass


def set_default_account_for_mode_of_payment(mode_of_payment, company, account):
	mode_of_payment.reload()
	if frappe.db.exists(
		"Mode of Payment Account", {"parent": mode_of_payment.mode_of_payment, "company": company}
	):
		frappe.db.set_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment.mode_of_payment, "company": company},
			"default_account",
			account,
		)
		return

	mode_of_payment.append("accounts", {"company": company, "default_account": account})
	mode_of_payment.save()
=======

import unittest

# test_records = frappe.get_test_records('Mode of Payment')


class TestModeofPayment(unittest.TestCase):
	pass
>>>>>>> 7c4cf3e834 (Favicon.svg)
