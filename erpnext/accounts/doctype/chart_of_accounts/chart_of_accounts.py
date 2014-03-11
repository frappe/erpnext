# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def create_accounts(self, company):
		chart = {}
		with open(os.path.join(os.path.dirname(__file__), "charts", 
			self.doc.source_file), "r") as f:
			chart = json.loads(f.read())
			
		if chart:
			accounts = []
			def _import_accounts(children, parent):
				for child in children:
					account_name = child.get("name")
					account_name_in_db = unidecode(account_name.strip().lower())
					
					if account_name_in_db in accounts:
						count = accounts.count(account_name_in_db)
						account_name = account_name + " " + cstr(count)
											
					account = frappe.bean({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"group_or_ledger": "Group" if child.get("children") else "Ledger",
						"root_type": child.get("root_type"),
						"is_pl_account": "Yes" if child.get("root_type") in ["Expense", "Income"] \
							else "No",
						"account_type": child.get("account_type")
					}).insert()
				
					accounts.append(account_name_in_db)
					# print account.doc.lft, account.doc.rgt, account.doc.root_type
			
					if child.get("children"):
						_import_accounts(child.get("children"), account.doc.name)
			
			_import_accounts(chart.get("root").get("children"), None)
		
			# set root_type from parent or child if not set
			# root_types = frappe.db.sql("""select lft, rgt, distinct root_type from tabAccount 
			# 	where ifnull(root_type, '') != '' order by lft desc""")
			# print root_types
		
		