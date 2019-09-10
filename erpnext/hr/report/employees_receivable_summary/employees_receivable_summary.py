# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary \
	import AccountsReceivableSummary

def execute(filters=None):
	args = {
		"party_type": "Employee",
		"naming_by": ["HR Settings", "emp_created_by"],
	}
	return AccountsReceivableSummary(filters).run(args)

