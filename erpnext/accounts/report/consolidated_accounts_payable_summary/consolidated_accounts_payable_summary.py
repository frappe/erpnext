# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from erpnext.accounts.report.consolidated_accounts_receivable_summary.consolidated_accounts_receivable_summary import (
	ConsolidatedReceivablePayableSummary,
)


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return ConsolidatedReceivablePayableSummary(filters).run(args)
