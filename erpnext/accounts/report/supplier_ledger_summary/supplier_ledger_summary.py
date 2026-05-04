# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import (
	PartyLedgerSummaryReport,
)


def execute(filters=None):
	args = {
		"party_type": "Supplier",
	}
	return PartyLedgerSummaryReport(filters).run(args)
