# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import PartyLedgerSummaryReport

def execute(filters=None):
	args = {
		"party_type": "Employee",
		"naming_by": ["HR Settings", "emp_created_by"],
	}
	return PartyLedgerSummaryReport(filters).run(args)