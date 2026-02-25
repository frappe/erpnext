# Copyright (c) 2015, Hash Include Solutions FZC and Contributors
# License: GNU General Public License v3. See license.txt


from perceptrons.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return ReceivablePayableReport(filters).run(args)
