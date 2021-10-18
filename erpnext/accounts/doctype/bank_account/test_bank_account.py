# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.accounts.doctype.bank_account.bank_account import validate_iban


class TestBankAccount(unittest.TestCase):

	def setUp(self):
		frappe.db.sql("delete from tabBank")
		frappe.db.sql("delete from `tabBank Account`")
		create_bank()

	def test_bank_account_creation(self):
		doc = frappe.new_doc("Bank Account")
		doc.account_name = "Coop Account"
		doc.bank = "Coop Bank"
		doc.iban = "GB82 WEST 1234 5698 7654 38"
		doc.save()

	def test_iban_validation_failure(self):
		doc = frappe.new_doc("Bank Account")
		doc.account_name = "iban test"
		doc.iban = "GB82 WEST 1234 5698 3333 12"
		doc.bank = "Coop Bank"

		with self.assertRaises(frappe.exceptions.ValidationError):
			doc.save()

def create_bank():
	doc = frappe.new_doc("Bank")
	doc.bank_name = "Coop Bank"
	doc.swift_number = "CoWTC"
	doc.save()