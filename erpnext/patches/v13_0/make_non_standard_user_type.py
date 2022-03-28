# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe

from erpnext.setup.install import add_non_standard_user_types


def execute():
	doctype_dict = {
		"projects": ["Timesheet"],
		"payroll": [
			"Salary Slip",
			"Employee Tax Exemption Declaration",
			"Employee Tax Exemption Proof Submission",
			"Employee Benefit Application",
			"Employee Benefit Claim",
		],
		"hr": [
			"Employee",
			"Expense Claim",
			"Leave Application",
			"Attendance Request",
			"Compensatory Leave Request",
			"Holiday List",
			"Employee Advance",
			"Training Program",
			"Training Feedback",
			"Shift Request",
			"Employee Grievance",
			"Employee Referral",
			"Travel Request",
		],
	}

	for module, doctypes in doctype_dict.items():
		for doctype in doctypes:
			frappe.reload_doc(module, "doctype", doctype)

	frappe.flags.ignore_select_perm = True
	frappe.flags.update_select_perm_after_migrate = True

	add_non_standard_user_types()
