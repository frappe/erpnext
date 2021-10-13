# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


class TestBankAccount(unittest.TestCase):

	def setUp(self):
		create_bank()

	def test_bank_account_creation(self):
		doc = frappe.new_doc("Bank Account")
		doc.account_name = "Test Account"
		doc.bank = "Test Bank"
		doc.iban = "GB82 WEST 1234 5698 7654 32"
		doc.save()

def create_bank():
	doc = frappe.new_doc("Bank")
	doc.bank_name = "Test Bank"
	doc.swift_number = "TBWTC"
	doc.save()