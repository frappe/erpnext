# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.test_runner import make_test_records
from frappe.utils import add_days, nowdate

contract_test_records = frappe.get_test_records('Contract')
make_test_records('Contract Template')
make_test_records("Customer", force=True)


class TestContract(unittest.TestCase):
	def setUp(self):
		self.contract_doc = frappe.copy_doc(contract_test_records[0])

		template_with_requirements = frappe.get_all("Contract Template", filters={"requires_fulfilment": 1})
		self.contract_template_with_requirements = template_with_requirements[0].name

		template_without_requirements = frappe.get_all("Contract Template", filters={"requires_fulfilment": 0})
		self.contract_template_without_requirements = template_without_requirements[0].name

	def test_validate_start_date_before_end_date(self):
		self.contract_doc.start_date = nowdate()
		self.contract_doc.end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

	def test_unsigned_contract_status(self):
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Unsigned")

	def test_active_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -1)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Active")

	def test_past_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), -1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_future_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), 1)
		self.contract_doc.end_date = add_days(nowdate(), 2)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_contract_status_with_no_fulfilment_terms(self):
		self.contract_doc.contract_terms = self.contract_template_without_requirements
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.fulfilment_status, "N/A")

	def test_unfulfilled_contract_status(self):
		self.contract_doc.contract_terms = self.contract_template_with_requirements
		self.contract_doc.save()
		self.contract_doc.insert()

		self.contract_doc.reload()

		self.assertEqual(self.contract_doc.fulfilment_status, "Unfulfilled")

	def test_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = self.contract_template_with_requirements
		self.contract_doc.save()
		self.contract_doc.insert()

		self.contract_doc.reload()

		# Mark all the terms as fulfilled
		for term in self.contract_doc.fulfilment_terms:
			term.fulfilled = 1

		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Fulfilled")

	def test_partially_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = self.contract_template_with_requirements
		self.contract_doc.insert()

		self.contract_doc.reload()

		# Mark only the first term as fulfilled
		self.contract_doc.fulfilment_terms[0].fulfilled = 1
		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Partially Fulfilled")

	def test_lapsed_contract_status(self):
		self.contract_doc.contract_terms = self.contract_template_with_requirements
		self.contract_doc.insert()

		self.contract_doc.reload()

		self.assertEqual(self.contract_doc.fulfilment_status, "Lapsed")
