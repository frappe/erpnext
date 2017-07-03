# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from frappe.utils import getdate

designations = {"name": "President", "designation_name": "President",
                "doctype": "Designation"}

period = {"end_date": "2017-06-30", "start_date": "2017-06-01",
          "doctype": "Payroll Period", "idx": "1"}

cycle_dict = {"cycle_name": '_Test Payment Cycle All Employees', "company_name": '_Test Company',
              "payroll_frequency": "Monthly", "doctype": "Payroll Cycle"}


def get_document(dt, designatione):
	designation = frappe.get_doc(designatione)
	if not frappe.db.exists(dt, designation.name):
		designation.insert()
	return designation


class TestPayrollCycle(unittest.TestCase):
	def setUp(self):
		get_document('Designation', designations)

	def test_create_payment_cycle(self):
		payroll_cycle = frappe.get_doc(cycle_dict)
		payroll_cycle.append("payment_period", period)

		payroll_cycle.save()

		self.assertEqual(
			getdate(payroll_cycle.payment_period[0].start_date),
			frappe.get_doc('Payroll Cycle', payroll_cycle.name).payment_period[0].start_date
		)

		self.assertEqual(
			getdate(payroll_cycle.payment_period[0].end_date),
			frappe.get_doc('Payroll Cycle', payroll_cycle.name).payment_period[0].end_date
		)
