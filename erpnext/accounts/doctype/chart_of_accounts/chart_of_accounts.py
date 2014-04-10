# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os, json
from frappe.utils import cstr
from unidecode import unidecode
from frappe.model.document import Document

class ChartofAccounts(Document):
	no_report_type = False
		
	def create_accounts(self, company):
		chart = {}
		with open(os.path.join(os.path.dirname(__file__), "charts", self.source_file), "r") as f:
			chart = json.loads(f.read())
			
		from erpnext.accounts.doctype.chart_of_accounts.charts.account_properties import account_properties
			
		if chart:
			accounts = []
			
			def _import_accounts(children, parent):
				for child in children:
					account_name = child.get("name")
					account_name_in_db = unidecode(account_name.strip().lower())
					
					if account_name_in_db in accounts:
						count = accounts.count(account_name_in_db)
						account_name = account_name + " " + cstr(count)

					child.update(account_properties.get(chart.get("name"), {}).get(account_name, {}))
					
					account = frappe.get_doc({
						"doctype": "Account",
						"account_name": account_name,
						"company": company,
						"parent_account": parent,
						"group_or_ledger": "Group" if child.get("children") else "Ledger",
						"report_type": child.get("report_type"),
						"account_type": child.get("account_type")
					}).insert()
					
					accounts.append(account_name_in_db)
					
					# set report_type for all parents where blank
					if not account.report_type or account.report_type == 'None':
						self.no_report_type = True
					elif self.no_report_type:
						frappe.db.sql("""update tabAccount set report_type=%s 
							where lft<=%s and rgt>=%s and ifnull(report_type, '')=''""", 
							(account.report_type, account.lft, account.rgt))
					
					if child.get("children"):
						_import_accounts(child.get("children"), account.name)
			
			_import_accounts(chart.get("root").get("children"), None)
			
@frappe.whitelist()
def get_charts_for_country(country):
	return frappe.db.sql_list("""select chart_name from `tabChart of Accounts` 
		where country=%s""", country)
