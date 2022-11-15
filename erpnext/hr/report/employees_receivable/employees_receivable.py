# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

def execute(filters=None):
	args = {
		"party_type": "Employee",
		"naming_by": ["HR Settings", "emp_created_by"],
	}
	return ReceivablePayableReport(filters).run(args)
