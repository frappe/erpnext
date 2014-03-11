# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("setup", 'doctype', "company")
	frappe.reload_doc("accounts", 'doctype', "account")
	
	frappe.db.sql("""update tabAccount set account_type='Fixed Asset' 
		where account_type='Fixed Asset Account'""")
		
	for d in (('Asset', 'Debit', 'No'), ('Liability', 'Credit', 'No'), ('Expense', 'Debit', 'Yes'), 
			('Income', 'Credit', 'Yes')):
		frappe.db.sql("""update `tabAccount` set root_type = %s 
			where debit_or_credit=%s and is_pl_account=%s""", d)
			
	frappe.db.sql("""update `tabAccount` set balance_must_be=debit_or_credit 
		where ifnull(allow_negative_balance, 0) = 0""")