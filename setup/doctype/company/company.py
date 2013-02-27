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

from webnotes.utils import cstr, set_default
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
	
	# Create default accounts
	# ---------------------------------------------------
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
					['Stock In Hand','Current Assets','Group','No','','Debit',self.doc.name,''],
						['Stock','Stock In Hand','Ledger','No','','Debit',self.doc.name,''],
					['Tax Assets','Current Assets','Group','No','','Debit',self.doc.name,''],
					['Stock Delivered But Not Billed','Current Assets','Ledger','No','','Debit',self.doc.name,''],
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
					['Cost of Goods Sold','Direct Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Expenses Included In Valuation','Direct Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
					['Stock Adjustment','Direct Expenses','Ledger','Yes','Expense Account','Debit',self.doc.name,''],
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
					['Duties and Taxes','Current Liabilities','Group','No','','Credit',self.doc.name,''],
					['Loans (Liabilities)','Current Liabilities','Group','No','','Credit',self.doc.name,''],
						['Secured Loans','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
						['Unsecured Loans','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
						['Bank Overdraft Account','Loans (Liabilities)','Group','No','','Credit',self.doc.name,''],
					['Stock Received But Not Billed','Current Liabilities','Ledger','No','','Credit',self.doc.name,''],
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

		country = sql("select value from tabSingles where field = 'country' and doctype = 'Control Panel'")
		country = country and cstr(country[0][0]) or ''

		# load taxes (only for India)
		if country == 'India':
			for d in acc_list_india:
				self.add_acc(d)

	# Create account
	# ---------------------------------------------------
	def add_acc(self,lst):
		ac = Document('Account')
		for d in self.fld_dict.keys():
			ac.fields[d] = (d == 'parent_account' and lst[self.fld_dict[d]]) and lst[self.fld_dict[d]] +' - '+ self.doc.abbr or lst[self.fld_dict[d]]
		ac_obj = get_obj(doc=ac)
		ac_obj.doc.freeze_account='No'
		ac_obj.doc.master_type = ''
		ac_obj.validate()
		ac_obj.doc.save(1)
		ac_obj.on_update()


	# Set letter head
	# ---------------------------------------------------
	def set_letter_head(self):
		if not self.doc.letter_head:
			if self.doc.address:
				header = """ 
<div><h3> %(comp)s </h3> %(add)s </div>

			""" % {'comp':self.doc.name,
				 'add':self.doc.address.replace("\n",'<br>')}
			 
				self.doc.letter_head = header

	# Set default AR and AP group
	# ---------------------------------------------------
	def set_default_groups(self):
		if not self.doc.receivables_group:
			webnotes.conn.set(self.doc, 'receivables_group', 'Accounts Receivable - '+self.doc.abbr)
		if not self.doc.payables_group:
			webnotes.conn.set(self.doc, 'payables_group', 'Accounts Payable - '+self.doc.abbr)
			
			
	# Create default cost center
	# ---------------------------------------------------
	def create_default_cost_center(self):
		from accounts.utils import add_cc
		cc_list = [
			{
				'cost_center_name':'Root',
				'company_name':self.doc.name,
				'group_or_ledger':'Group',
				'parent_cost_center':''
			}, 
			{
				'cost_center_name':'Default CC Ledger', 
				'company_name':self.doc.name,
				'group_or_ledger':'Ledger',
				'parent_cost_center':'Root - ' + self.doc.abbr
			}
		]
		for cc in cc_list:
			add_cc(cc)
			
	def on_update(self):
		self.set_letter_head()
		ac = sql("select name from tabAccount where company=%s and docstatus<2 limit 1",
			self.doc.name)
		if not ac:
			self.create_default_accounts()
		self.set_default_groups()
		cc = sql("select name from `tabCost Center` where cost_center_name = 'Root' and company_name = '%s'"%(self.doc.name))
		if not cc:
			self.create_default_cost_center()
			
		if self.doc.default_currency:
			webnotes.conn.set_value("Currency", self.doc.default_currency, "enabled", 1)

	def on_trash(self):
		"""
			Trash accounts and cost centers for this company if no gl entry exists
		"""
		rec = sql("SELECT name from `tabGL Entry` where ifnull(is_cancelled, 'No') = 'No' and company = %s", self.doc.name)
		if not rec:
			# delete gl entry
			sql("delete from `tabGL Entry` where company = %s", self.doc.name)

			#delete tabAccount
			sql("delete from `tabAccount` where company = %s order by lft desc, rgt desc", self.doc.name)
			
			#delete cost center child table - budget detail
			sql("delete bd.* from `tabBudget Detail` bd, `tabCost Center` cc where bd.parent = cc.name and cc.company_name = %s", self.doc.name)
			#delete cost center
			sql("delete from `tabCost Center` WHERE company_name = %s order by lft desc, rgt desc", self.doc.name)
			
			webnotes.defaults.clear_default("company", value=self.doc.name)
			
			#update value as blank for tabSingles Global Defaults
			sql("update `tabSingles` set value = '' where doctype='Global Defaults' and field = 'default_company' and value = %s", self.doc.name)

		
	# on rename
	# ---------
	def on_rename(self,newdn,olddn):
		sql("update `tabCompany` set company_name = '%s' where name = '%s'" %(newdn,olddn))	
		sql("update `tabSingles` set value = %s where doctype='Global Defaults' and field = 'default_company' and value = %s", (newdn, olddn))	
		if webnotes.defaults.get_global_default('company') == olddn:
			webnotes.defaults.set_global_default('company', newdn)