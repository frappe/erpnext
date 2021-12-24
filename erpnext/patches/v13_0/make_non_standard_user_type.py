# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from six import iteritems

from erpnext.setup.install import add_non_standard_user_types


def execute():
	doctype_dict = {
		'projects': ['Timesheet'],
		'payroll': ['Salary Slip', 'Employee Tax Exemption Declaration', 'Employee Tax Exemption Proof Submission'],
		'hr': ['Employee', 'Expense Claim', 'Leave Application', 'Attendance Request', 'Compensatory Leave Request']
	}

	for module, doctypes in iteritems(doctype_dict):
		for doctype in doctypes:
			frappe.reload_doc(module, 'doctype', doctype)


	frappe.flags.ignore_select_perm = True
	frappe.flags.update_select_perm_after_migrate = True

	add_non_standard_user_types()
