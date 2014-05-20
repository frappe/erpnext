# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "account")

	account_table_columns = frappe.db.get_table_columns("Account")
	if "debit_or_credit" in account_table_columns and "is_pl_account" in account_table_columns:
		frappe.db.sql("""UPDATE tabAccount SET root_type = CASE
			WHEN (debit_or_credit='Debit' and is_pl_account = 'No') THEN 'Asset'
			WHEN (debit_or_credit='Credit' and is_pl_account = 'No') THEN 'Liability'
			WHEN (debit_or_credit='Debit' and is_pl_account = 'Yes') THEN 'Expense'
			WHEN (debit_or_credit='Credit' and is_pl_account = 'Yes') THEN 'Income'
			END""")

	else:
		frappe.db.sql("""UPDATE tabAccount
			SET root_type = CASE
				WHEN name like '%%asset%%' THEN 'Asset'
				WHEN name like '%%liabilities%%' THEN 'Liability'
				WHEN name like '%%expense%%' THEN 'Expense'
				WHEN name like '%%income%%' THEN 'Income'
				END
			WHERE
				ifnull(parent_account, '') = ''
		""")

		for root in frappe.db.sql("""SELECT lft, rgt, root_type FROM `tabAccount`
			WHERE ifnull(parent_account, '')=''""",	as_dict=True):
				frappe.db.sql("""UPDATE tabAccount SET root_type=%s WHERE lft>%s and rgt<%s""",
					(root.root_type, root.lft, root.rgt))
