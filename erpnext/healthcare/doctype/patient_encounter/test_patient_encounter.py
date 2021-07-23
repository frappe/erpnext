# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest

import pymysql

import frappe
from frappe.exceptions import DuplicateEntryError

test_records = frappe.get_test_records('Patient Encounter')
print(test_records)

class TestPatientEncounter(unittest.TestCase):
	def test_treatment_plans_filter(self):
		try:
			frappe.get_doc(test_records[0]).insert()
		except DuplicateEntryError:
			pass

		encounter = frappe.get_list('Patient Encounter')
		print(encounter)
		encounter = frappe.get_doc('Patient Encounter', 'TPE-0001')
		plans = PatientEncounter.get_applicable_treatment_plans(encounter)

		assert plans[0]['name'] == 'Chemo'
