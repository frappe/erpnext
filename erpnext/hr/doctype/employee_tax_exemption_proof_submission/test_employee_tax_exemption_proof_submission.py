# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
# from erpnext.hr.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import create_exemption_category, create_payroll_period
#
# class TestEmployeeTaxExemptionProofSubmission(unittest.TestCase):
# 	def setup(self):
# 		make_employee("employee@proofsubmission.com")
# 		create_payroll_period()
# 		create_exemption_category()
# 		frappe.db.sql("""delete from `tabEmployee Tax Exemption Proof Submission`""")
#
# 	def test_exemption_amount_lesser_than_category_max(self):
# 		declaration = frappe.get_doc({
# 			"doctype": "Employee Tax Exemption Proof Submission",
# 			"employee": frappe.get_value("Employee", {"user_id":"employee@proofsubmission.com"}, "name"),
# 			"payroll_period": "Test Payroll Period",
# 			"tax_exemption_proofs": [dict(exemption_sub_category = "_Test Sub Category",
# 							type_of_proof = "Test Proof",
# 							exemption_category = "_Test Category",
# 							amount = 150000)]
# 		})
# 		self.assertRaises(frappe.ValidationError, declaration.save)
# 		declaration = frappe.get_doc({
# 			"doctype": "Employee Tax Exemption Proof Submission",
# 			"payroll_period": "Test Payroll Period",
# 			"employee": frappe.get_value("Employee", {"user_id":"employee@proofsubmission.com"}, "name"),
# 			"tax_exemption_proofs": [dict(exemption_sub_category = "_Test Sub Category",
# 							type_of_proof = "Test Proof",
# 							exemption_category = "_Test Category",
# 							amount = 100000)]
# 		})
# 		self.assertTrue(declaration.save)
# 		self.assertTrue(declaration.submit)
#
# 	def test_duplicate_category_in_proof_submission(self):
# 		declaration = frappe.get_doc({
# 			"doctype": "Employee Tax Exemption Proof Submission",
# 			"employee": frappe.get_value("Employee", {"user_id":"employee@proofsubmission.com"}, "name"),
# 			"payroll_period": "Test Payroll Period",
# 			"tax_exemption_proofs": [dict(exemption_sub_category = "_Test Sub Category",
# 							exemption_category = "_Test Category",
# 							type_of_proof = "Test Proof",
# 							amount = 100000),
# 							dict(exemption_sub_category = "_Test Sub Category",
# 							exemption_category = "_Test Category",
# 							amount = 50000),
# 							]
# 		})
# 		self.assertRaises(frappe.ValidationError, declaration.save)
