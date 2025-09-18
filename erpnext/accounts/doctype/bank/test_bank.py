# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase


class TestBank(IntegrationTestCase):
	pass


def create_bank(**kwargs):
	bank_doc = None
	if bank := frappe.db.exists("Bank", kwargs.get("bank_name", "_Test Bank")):
		bank_doc = frappe.get_doc("Bank", bank)
	else:
		bank_doc = frappe.new_doc("Bank")
		bank_doc.bank_name = kwargs.get("bank_name", "_Test Bank")
		bank_doc.insert()

	if kwargs.get("return_doc"):
		return bank_doc

	return bank_doc.name
