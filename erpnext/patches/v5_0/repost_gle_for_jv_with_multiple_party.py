# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	je_list = frappe.db.sql_list("""
		select par.name from `tabJournal Entry` par 
		where par.docstatus=1 and par.creation > '2015-03-01'
			and (select count(distinct child.party) from `tabJournal Entry Account` child
				where par.name=child.parent and ifnull(child.party, '') != '') > 1	
	""")
	
	for d in je_list:		
		# delete existing gle
		frappe.db.sql("delete from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s", d)
		
		# repost gl entries
		je = frappe.get_doc("Journal Entry", d)
		je.make_gl_entries()
		
	if je_list:
		print je_list
		
		