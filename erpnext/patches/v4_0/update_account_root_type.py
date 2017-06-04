# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "account")

	account_table_columns = frappe.db.get_table_columns("Account")
	if "debit_or_credit" in account_table_columns and "is_pl_account" in account_table_columns:
		frappe.db.sql("""UPDATE tabAccount
			SET root_type = CASE
				WHEN (debit_or_credit='Debit' and is_pl_account = 'No') THEN 'Asset'
				WHEN (debit_or_credit='Credit' and is_pl_account = 'No') THEN 'Liability'
				WHEN (debit_or_credit='Debit' and is_pl_account = 'Yes') THEN 'Expense'
				WHEN (debit_or_credit='Credit' and is_pl_account = 'Yes') THEN 'Income'
				END
			WHERE ifnull(parent_account, '') = ''
		""")

	else:
		for key, root_type in (("asset", "Asset"), ("liabilities", "Liability"), ("expense", "Expense"),
			("income", "Income")):
			frappe.db.sql("""update tabAccount set root_type=%s where name like %s
				and ifnull(parent_account, '')=''""", (root_type, "%" + key + "%"))

	for root in frappe.db.sql("""SELECT name, lft, rgt, root_type FROM `tabAccount`
		WHERE ifnull(parent_account, '')=''""",	as_dict=True):
			if root.root_type:
				frappe.db.sql("""UPDATE tabAccount SET root_type=%s WHERE lft>%s and rgt<%s""",
					(root.root_type, root.lft, root.rgt))
			else:
				print b"Root type not found for {0}".format(root.name.encode("utf-8"))
