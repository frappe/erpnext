# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		self.no_root_type = False
		
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
						"account_type": child.get("account_type")
					}).insert()
				
					accounts.append(account_name_in_db)
					
					# set root_type for all parents where blank
					if not account.doc.root_type or account.doc.root_type == 'None':
						self.no_root_type = True
					elif self.no_root_type:
						frappe.db.sql("""update tabAccount set root_type=%s 
							where lft<=%s and rgt>=%s and ifnull(root_type, '')=''""", 
							(account.doc.root_type, account.doc.lft, account.doc.rgt))
					
					if child.get("children"):
						_import_accounts(child.get("children"), account.doc.name)
			
			_import_accounts(chart.get("root").get("children"), None)
			
			# set root_type for root accounts
			for acc in frappe.db.sql("""select name, lft, rgt from `tabAccount` 
				where ifnull(parent_account, '')=''""", as_dict=1):
					root_types = frappe.db.sql_list("""select distinct root_type from tabAccount 
						where lft>%s and rgt<%s""", (acc.lft, acc.rgt))
					if len(root_types) > 1:
						frappe.db.set_value("Account", acc.name, "root_type", None)