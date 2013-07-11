# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint

from webnotes.utils import cstr
from webnotes.model.doc import Document
from webnotes.model.code import get_obj
import webnotes.defaults

sql = webnotes.conn.sql

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl
		
	def validate(self):
		if self.doc.fields.get('__islocal') and len(self.doc.abbr) > 5:
			webnotes.msgprint("Abbreviation cannot have more than 5 characters",
				raise_exception=1)

	def on_update(self):
		if not webnotes.conn.sql("""select name from tabAccount 
			where company=%s and docstatus<2 limit 1""", self.doc.name):
			self.create_default_accounts()
			self.create_default_warehouses()
			self.create_default_web_page()
		
		if not self.doc.cost_center:
			self.create_default_cost_center()
			
		self.set_default_accounts()

		if self.doc.default_currency:
			webnotes.conn.set_value("Currency", self.doc.default_currency, "enabled", 1)

	def create_default_warehouses(self):
		for whname in ("Stores", "Work In Progress", "Finished Goods"):
			webnotes.bean({
				"doctype":"Warehouse",
				"warehouse_name": whname,
				"company": self.doc.name
			}).insert()
			
	def create_default_web_page(self):
		if not webnotes.conn.get_value("Website Settings", None, "home_page"):
			import os
			with open(os.path.join(os.path.dirname(__file__), "sample_home_page.html"), "r") as webfile:
				webpage = webnotes.bean({
					"doctype": "Web Page",
					"title": self.doc.name + " Home",
					"published": 1,
					"description": "Standard Home Page for " + self.doc.company,
					"main_section": webfile.read() % self.doc.fields
				}).insert()
			
				# update in home page in settings
				website_settings = webnotes.bean("Website Settings", "Website Settings")
				website_settings.doc.home_page = webpage.doc.name
				website_settings.doc.banner_html = """<h3 style='margin-bottom: 20px;'>""" + self.doc.name + "</h3>"
				website_settings.doc.copyright = self.doc.name
				website_settings.doclist.append({
					"doctype": "Top Bar Item",
					"parentfield": "top_bar_items",
					"label":"Home",
					"url": webpage.doc.name
				})
				website_settings.doclist.append({
					"doctype": "Top Bar Item",
					"parentfield": "top_bar_items",
					"label":"Contact",
					"url": "contact"
				})
				website_settings.doclist.append({
					"doctype": "Top Bar Item",
					"parentfield": "top_bar_items",
					"label":"Blog",
					"url": "blog"
				})
				website_settings.save()

	def create_default_accounts(self):
		self.fld_dict = {'account_name':0,'parent_account':1,'group_or_ledger':2,'is_pl_account':3,'account_type':4,'debit_or_credit':5,'company':6,'tax_rate':7}
		acc_list_common = [
			['Application of Funds (Assets)','','Group','No','','Debit',self.doc.name,''],
				['Current Assets','Application of Funds (Assets)','Group','No','','Debit',self.doc.name,''],
					['Accounts Receivable','Current Assets','Group','No','','Debit',self.doc.name,''],
					['Bank Accounts','Current Assets','Group','No','Bank or Cash','Debit',self.doc.name,''],
					['Cash In Hand','Current Assets','Group','No','Bank or Cash','Debit',self.doc.name,''],
						['Cash','Cash In Hand','Ledger','No','Bank or Cash','Debit',self.doc.name,''],
					['Loans and Advances (Assets)','Current Assets','Group','No','','Debit',self.doc.name,''],
					['Securities and Deposits','Current Assets','Group','No','','Debit',self.doc.name,''],
						['Earnest Money','Securities and Deposits','Ledger','No','','Debit',self.doc.name,''],
					['Stock Assets','Current Assets','Group','No','','Debit',self.doc.name,''],
						['Stock In Hand','Stock Assets','Ledger','No','','Debit',self.doc.name,''],
					['Tax Assets','Current Assets','Group','No','','Debit',self.doc.name,''],
				['Fixed Assets','Application of Funds (Assets)','Group','No','','Debit',self.doc.name,''],
					['Capital Equipments','Fixed Assets','Ledger','No','Fixed Asset Account','Debit',self.doc.name,''],
					['Computers','Fixed Assets','Ledger','No','Fixed Asset Account','Debit',self.doc.name,''],
					['Furniture and Fixture','Fixed Assets','Ledger','No','Fixed Asset Account','Debit',self.doc.name,''],
					['Office Equipments','Fixed Assets','Ledger','No','Fixed Asset Account','Debit',self.doc.name,''],
					['Plant and Machinery','Fixed Assets','Ledger','No','Fixed Asset Account','Debit',self.doc.name,''],
				['Investments','Application of Funds (Assets)','Group','No','','Debit',self.doc.name,''],
				['Temporary Accounts (Assets)','Application of Funds (Assets)','Group','No','','Debit',self.doc.name,''],
					['Temporary Account (Assets)','Temporary Accounts (Assets)','Ledger','No','','Debit',self.doc.name,''],
			['Expenses','','Group','Yes','Expense Account','Debit',self.doc.name,''],
				['Direct Expenses','Expenses','Group','Yes','Expense Account','Debit',self.doc.name,''],
					['Stock Expenses','Direct Expenses','Group','Yes','Expense Account','Debit',self.doc.name,''],
						['Cost of Goods Sold','Stock Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
						['Stock Adjustment','Stock Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
						['Expenses Included In Valuation', "Stock Expenses", 'Ledger', 'Yes', 'Expense Account', 'Debit', self.doc.name, ''],
				['Indirect Expenses','Expenses','Group','Yes','Expense Account','Debit',self.doc.name,''],
					['Advertising and Publicity','Indirect Expenses','Ledger','Yes','Chargeable','Debit',self.doc.name,''],
					['Bad Debts Written Off','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Bank Charges','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Books and Periodicals','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Charity and Donations','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Commission on Sales','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Conveyance Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Customer Entertainment Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Depreciation Account','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Freight and Forwarding Charges','Indirect Expenses','Ledger','Yes','Chargeable','Debit',self.doc.name,''],
					['Legal Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Miscellaneous Expenses','Indirect Expenses','Ledger','Yes','Chargeable','Debit',self.doc.name,''],
					['Office Maintenance Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Office Rent','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Postal Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Print and Stationary','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Rounded Off','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Salary','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Sales Promotion Expenses','Indirect Expenses','Ledger','Yes','Chargeable','Debit',self.doc.name,''],
					['Service Charges Paid','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Staff Welfare Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Telephone Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Travelling Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Water and Electricity Expenses','Indirect Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
			['Income','','Group','Yes','','Credit',self.doc.name,''],
				['Direct Income','Income','Group','Yes','Income Account','Credit',self.doc.name,''],
					['Sales','Direct Income','Ledger','Yes','Income Account','Credit',self.doc.name,''],
					['Service','Direct Income','Ledger','Yes','Income Account','Credit',self.doc.name,''],
				['Indirect Income','Income','Group','Yes','Income Account','Credit',self.doc.name,''],
			['Source of Funds (Liabilities)','','Group','No','','Credit',self.doc.name,''],
				['Capital Account','Source of Funds (Liabilities)','Group','No','','Credit',self.doc.name,''],
					['Reserves and Surplus','Capital Account','Group','No','','Credit',self.doc.name,''],
					['Shareholders Funds','Capital Account','Group','No','','Credit',self.doc.name,''],
				['Current Liabilities','Source of Funds (Liabilities)','Group','No','','Credit',self.doc.name,''],
					['Accounts Payable','Current Liabilities','Group','No','','Credit',self.doc.name,''],
					['Stock Liabilities','Current Liabilities','Group','No','','Credit',self.doc.name,''],
						['Stock Received But Not Billed', 'Stock Liabilities', 'Ledger', 
							'No', '', 'Credit', self.doc.name, ''],					
					['Duties and Taxes','Current Liabilities','Group','No','','Credit',self.doc.name,''],
					['Loans (Liabilities)','Current Liabilities','Group','No','','Credit',self.doc.name,''],
						['Secured Loans','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
						['Unsecured Loans','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
						['Bank Overdraft Account','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
				['Temporary Accounts (Liabilities)','Source of Funds (Liabilities)','Group','No','','Credit',self.doc.name,''],
					['Temporary Account (Liabilities)','Temporary Accounts (Liabilities)','Ledger','No','','Credit',self.doc.name,'']
		]
		
		acc_list_india = [
			['CENVAT Capital Goods','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT Service Tax','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT Service Tax Cess 1','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT Service Tax Cess 2','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT Edu Cess','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['CENVAT SHE Cess','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['Excise Duty 4','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'4.00'],
			['Excise Duty 8','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'8.00'],
			['Excise Duty 10','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'10.00'],
			['Excise Duty 14','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'14.00'],
			['Excise Duty Edu Cess 2','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'2.00'],
			['Excise Duty SHE Cess 1','Tax Assets','Ledger','No','Tax','Debit',self.doc.name,'1.00'],
			['P L A','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['P L A - Cess Portion','Tax Assets','Ledger','No','Chargeable','Debit',self.doc.name,''],
			['Edu. Cess on Excise','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'2.00'],
			['Edu. Cess on Service Tax','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'2.00'],
			['Edu. Cess on TDS','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'2.00'],
			['Excise Duty @ 4','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'4.00'],
			['Excise Duty @ 8','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'8.00'],
			['Excise Duty @ 10','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'10.00'],
			['Excise Duty @ 14','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'14.00'],
			['Service Tax','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'10.3'],
			['SHE Cess on Excise','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'1.00'],
			['SHE Cess on Service Tax','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'1.00'],
			['SHE Cess on TDS','Duties and Taxes','Ledger','No','Tax','Credit',self.doc.name,'1.00'],
			['Professional Tax','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['VAT','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Advertisement)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Commission)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Contractor)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Interest)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Rent)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,''],
			['TDS (Salary)','Duties and Taxes','Ledger','No','Chargeable','Credit',self.doc.name,'']
		 ]
		# load common account heads
		for d in acc_list_common:
			self.add_acc(d)

		country = webnotes.conn.sql("select value from tabSingles where field = 'country' and doctype = 'Control Panel'")
		country = country and cstr(country[0][0]) or ''

		# load taxes (only for India)
		if country == 'India':
			for d in acc_list_india:
				self.add_acc(d)

	def add_acc(self,lst):
		account = webnotes.bean({
			"doctype": "Account",
			"freeze_account": "No",
			"master_type": "",
		})
		for d in self.fld_dict.keys():
			account.doc.fields[d] = (d == 'parent_account' and lst[self.fld_dict[d]]) and lst[self.fld_dict[d]] +' - '+ self.doc.abbr or lst[self.fld_dict[d]]
			
		account.insert()

	def set_default_accounts(self):
		accounts = {
			"default_income_account": "Sales",
			"default_expense_account": "Cost of Goods Sold",
			"receivables_group": "Accounts Receivable",
			"payables_group": "Accounts Payable",
			"stock_received_but_not_billed": "Stock Received But Not Billed",
			"stock_in_hand_account": "Stock In Hand",
			"stock_adjustment_account": "Stock Adjustment",
			"expenses_included_in_valuation": "Expenses Included In Valuation"
		}
		
		for a in accounts:
			account_name = accounts[a] + " - " + self.doc.abbr
			if not self.doc.fields.get(a) and webnotes.conn.exists("Account", account_name):
				webnotes.conn.set(self.doc, a, account_name)

		if not self.doc.stock_adjustment_cost_center:
				webnotes.conn.set(self.doc, "stock_adjustment_cost_center", self.doc.cost_center)

	def create_default_cost_center(self):
		cc_list = [
			{
				'cost_center_name': self.doc.name,
				'company':self.doc.name,
				'group_or_ledger':'Group',
				'parent_cost_center':''
			}, 
			{
				'cost_center_name':'Main', 
				'company':self.doc.name,
				'group_or_ledger':'Ledger',
				'parent_cost_center':self.doc.name + ' - ' + self.doc.abbr
			},
		]
		for cc in cc_list:
			cc.update({"doctype": "Cost Center"})
			cc_bean = webnotes.bean(cc)
			cc_bean.ignore_permissions = True
			
			if cc.get("cost_center_name") == self.doc.name:
				cc_bean.ignore_mandatory = True
			
			cc_bean.insert()
			
		webnotes.conn.set(self.doc, "cost_center", "Main - " + self.doc.abbr)

	def on_trash(self):
		"""
			Trash accounts and cost centers for this company if no gl entry exists
		"""
		rec = webnotes.conn.sql("SELECT name from `tabGL Entry` where ifnull(is_cancelled, 'No') = 'No' and company = %s", self.doc.name)
		if not rec:
			# delete gl entry
			webnotes.conn.sql("delete from `tabGL Entry` where company = %s", self.doc.name)

			#delete tabAccount
			webnotes.conn.sql("delete from `tabAccount` where company = %s order by lft desc, rgt desc", self.doc.name)
			
			#delete cost center child table - budget detail
			webnotes.conn.sql("delete bd.* from `tabBudget Detail` bd, `tabCost Center` cc where bd.parent = cc.name and cc.company = %s", self.doc.name)
			#delete cost center
			webnotes.conn.sql("delete from `tabCost Center` WHERE company = %s order by lft desc, rgt desc", self.doc.name)
			
		webnotes.defaults.clear_default("company", value=self.doc.name)
			
		webnotes.conn.sql("""update `tabSingles` set value=""
			where doctype='Global Defaults' and field='default_company' 
			and value=%s""", self.doc.name)
			
	def on_rename(self,newdn,olddn, merge=False):
		if merge:
			msgprint(_("Sorry. Companies cannot be merged"), raise_exception=True)
		
		webnotes.conn.sql("""update `tabCompany` set company_name=%s
			where name=%s""", (newdn, olddn))
		
		webnotes.conn.sql("""update `tabSingles` set value=%s
			where doctype='Global Defaults' and field='default_company' 
			and value=%s""", (newdn, olddn))
		
		webnotes.defaults.clear_default("company", value=olddn)