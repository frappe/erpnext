# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def create_accounts(self, company):
		with open(os.path.join(os.path.dirname(__file__), "charts", 
			self.doc.source_file), "r") as f:
			chart = json.loads(f.read())

		def _import_accounts(children, parent):
			for child in children:
				print child.get("name"), parent
				account = frappe.bean({
					"doctype": "Account",
					"account_name": child.get("name"),
					"company": company,
					"parent_account": parent,
					"group_or_ledger": "Group" if child.get("children") else "Ledger",
					"root_type": child.get("root_type"),
					"is_pl_account": "Yes" if child.get("root_type") in ["Expense", "Income"] \
						else "No",
					"account_type": child.get("account_type")
				}).insert()
			
				if child.get("children"):
					_import_accounts(child.get("children"), account.doc.name)
			
		_import_accounts(chart.get("root").get("children"), None)