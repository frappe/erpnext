# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import Count

from erpnext.accounts.doctype.bank_account_balance.bank_account_balance import on_doctype_update


def execute():
	if not frappe.db.table_exists("Bank Account Balance"):
		return

	balance = frappe.qb.DocType("Bank Account Balance")
	duplicates = (
		frappe.qb.from_(balance)
		.select(balance.bank_account, balance.date)
		.groupby(balance.bank_account, balance.date)
		.having(Count(balance.name) > 1)
		.run(as_dict=True)
	)
	for row in duplicates:
		balances = frappe.get_all(
			"Bank Account Balance",
			filters={"bank_account": row.bank_account, "date": row.date},
			order_by="modified desc, creation desc, name desc",
			pluck="name",
		)
		# Keep the latest correction; delete through the document API to retain deleted-document history.
		for name in balances[1:]:
			frappe.delete_doc("Bank Account Balance", name, ignore_permissions=True)

	on_doctype_update()
