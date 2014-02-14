# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.utils.nestedset import rebuild_tree
	rebuild_tree('Account', 'parent_account')

	roots = webnotes.conn.sql("""
		select lft, rgt, debit_or_credit, is_pl_account, company from `tabAccount`
		where ifnull(parent_account, '') = ''
	""", as_dict=1)

	for acc in roots:
		webnotes.conn.sql("""update tabAccount set debit_or_credit = %(debit_or_credit)s, 
			is_pl_account = %(is_pl_account)s, company = %(company)s
			where lft > %(lft)s and rgt < %(rgt)s""", acc)