# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint

from frappe.utils import cstr, cint
import frappe.defaults


from frappe.model.document import Document

class Company(Document):

		
	def onload(self):
		self.doc.fields["__transactions_exist"] = self.check_if_transactions_exist()
		
	def check_if_transactions_exist(self):
		exists = False
		for doctype in ["Sales Invoice", "Delivery Note", "Sales Order", "Quotation",
			"Purchase Invoice", "Purchase Receipt", "Purchase Order", "Supplier Quotation"]:
				if frappe.db.sql("""select name from `tab%s` where company=%s and docstatus=1
					limit 1""" % (doctype, "%s"), self.doc.name):
						exists = True
						break
		
		return exists
		
	def validate(self):
		if self.doc.fields.get('__islocal') and len(self.doc.abbr) > 5:
			frappe.msgprint("Abbreviation cannot have more than 5 characters",
				raise_exception=1)
				
		self.previous_default_currency = frappe.db.get_value("Company", self.doc.name, "default_currency")
		if self.doc.default_currency and self.previous_default_currency and \
			self.doc.default_currency != self.previous_default_currency and \
			self.check_if_transactions_exist():
				msgprint(_("Sorry! You cannot change company's default currency, because there are existing transactions against it. You will need to cancel those transactions if you want to change the default currency."), raise_exception=True)

	def on_update(self):
		if not frappe.db.sql("""select name from tabAccount 
			where company=%s and docstatus<2 limit 1""", self.doc.name):
			self.create_default_accounts()
			self.create_default_warehouses()
			self.create_default_web_page()
		
		if not frappe.db.get_value("Cost Center", {"group_or_ledger": "Ledger", 
				"company": self.doc.name}):
			self.create_default_cost_center()
			
		self.set_default_accounts()

		if self.doc.default_currency:
			frappe.db.set_value("Currency", self.doc.default_currency, "enabled", 1)

	def create_default_warehouses(self):
		for whname in ("Stores", "Work In Progress", "Finished Goods"):
			if not frappe.db.exists("Warehouse", whname + " - " + self.doc.abbr):
				stock_group = frappe.db.get_value("Account", {"account_type": "Stock", 
					"group_or_ledger": "Group"})
				if stock_group:
					frappe.bean({
						"doctype":"Warehouse",
						"warehouse_name": whname,
						"company": self.doc.name,
						"create_account_under": stock_group
					}).insert()
			
	def create_default_web_page(self):
		if not frappe.db.get_value("Website Settings", None, "home_page") and \
				not frappe.db.sql("select name from tabCompany where name!=%s", self.doc.name):
			import os
			with open(os.path.join(os.path.dirname(__file__), "sample_home_page.html"), "r") as webfile:
				webpage = frappe.bean({
					"doctype": "Web Page",
					"title": self.doc.name + " Home",
					"published": 1,
					"description": "Standard Home Page for " + self.doc.name,
					"main_section": webfile.read() % self.doc.fields
				}).insert()
			
				# update in home page in settings
				website_settings = frappe.bean("Website Settings", "Website Settings")
				website_settings.doc.home_page = webpage.doc.name
				website_settings.doc.brand_html = self.doc.name
				website_settings.doc.copyright = self.doc.name
				website_settings.append("top_bar_items", {
					"doctype": "Top Bar Item",
					"label":"Contact",
					"url": "contact"
				})
				website_settings.append("top_bar_items", {
					"doctype": "Top Bar Item",
					"label":"Blog",
					"url": "blog"
				})
				website_settings.save()
				style_settings = frappe.bean("Style Settings", "Style Settings")
				style_settings.doc.top_bar_background = "F2F2F2"
				style_settings.doc.font_size = "15px"
				style_settings.save()

	def create_default_accounts(self):
		if self.doc.chart_of_accounts:
			self.import_chart_of_account()
		else:
			self.create_standard_accounts()
			frappe.db.set(self.doc, "receivables_group", "Accounts Receivable - " + self.doc.abbr)
			frappe.db.set(self.doc, "payables_group", "Accounts Payable - " + self.doc.abbr)
			
	def import_chart_of_account(self):
		chart = frappe.bean("Chart of Accounts", self.doc.chart_of_accounts)
		chart.make_controller().create_accounts(self.doc.name)

	def add_acc(self,lst):
		account = frappe.bean({
			"doctype": "Account",
			"freeze_account": "No",
			"master_type": "",
		})
		
		for d in self.fld_dict.keys():
			account.doc.fields[d] = (d == 'parent_account' and lst[self.fld_dict[d]]) and lst[self.fld_dict[d]] +' - '+ self.doc.abbr or lst[self.fld_dict[d]]
		account.insert()

	def set_default_accounts(self):
		def _set_default_accounts(accounts):
			for field, account_type in accounts.items():
				account = frappe.db.get_value("Account", {"account_type": account_type, 
					"group_or_ledger": "Ledger", "company": self.doc.name})

				if account and not self.doc.fields.get(field):
					frappe.db.set(self.doc, field, account)
			
		_set_default_accounts({
			"default_cash_account": "Cash",
			"default_bank_account": "Bank"
		})
		
		if cint(frappe.db.get_value("Accounts Settings", None, "auto_accounting_for_stock")):
			_set_default_accounts({
				"stock_received_but_not_billed": "Stock Received But Not Billed",
				"stock_adjustment_account": "Stock Adjustment",
				"expenses_included_in_valuation": "Expenses Included In Valuation"
			})

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
			cc_bean = frappe.bean(cc)
			cc_bean.ignore_permissions = True
		
			if cc.get("cost_center_name") == self.doc.name:
				cc_bean.ignore_mandatory = True
			cc_bean.insert()
			
		frappe.db.set(self.doc, "cost_center", "Main - " + self.doc.abbr)

	def on_trash(self):
		"""
			Trash accounts and cost centers for this company if no gl entry exists
		"""
		rec = frappe.db.sql("SELECT name from `tabGL Entry` where company = %s", self.doc.name)
		if not rec:
			#delete tabAccount
			frappe.db.sql("delete from `tabAccount` where company = %s order by lft desc, rgt desc", self.doc.name)
			
			#delete cost center child table - budget detail
			frappe.db.sql("delete bd.* from `tabBudget Detail` bd, `tabCost Center` cc where bd.parent = cc.name and cc.company = %s", self.doc.name)
			#delete cost center
			frappe.db.sql("delete from `tabCost Center` WHERE company = %s order by lft desc, rgt desc", self.doc.name)
			
		if not frappe.db.get_value("Stock Ledger Entry", {"company": self.doc.name}):
			frappe.db.sql("""delete from `tabWarehouse` where company=%s""", self.doc.name)
			
		frappe.defaults.clear_default("company", value=self.doc.name)
			
		frappe.db.sql("""update `tabSingles` set value=""
			where doctype='Global Defaults' and field='default_company' 
			and value=%s""", self.doc.name)
			
	def before_rename(self, olddn, newdn, merge=False):
		if merge:
			frappe.throw(_("Sorry, companies cannot be merged"))
	
	def after_rename(self, olddn, newdn, merge=False):
		frappe.db.set(self.doc, "company_name", newdn)

		frappe.db.sql("""update `tabDefaultValue` set defvalue=%s 
			where defkey='Company' and defvalue=%s""", (newdn, olddn))

		frappe.defaults.clear_cache()
		
	def create_standard_accounts(self):
		self.fld_dict = {
			'account_name': 0,
			'parent_account': 1,
			'group_or_ledger': 2,
			'account_type': 3,
			'report_type': 4,
			'company': 5,
			'tax_rate': 6
		}
		
		acc_list_common = [
			['Application of Funds (Assets)','','Group','','Balance Sheet',self.doc.name,''],
				['Current Assets','Application of Funds (Assets)','Group','','Balance Sheet',self.doc.name,''],
					['Accounts Receivable','Current Assets','Group','','Balance Sheet',self.doc.name,''],
					['Bank Accounts','Current Assets','Group','Bank','Balance Sheet',self.doc.name,''],
					['Cash In Hand','Current Assets','Group','Cash','Balance Sheet',self.doc.name,''],
						['Cash','Cash In Hand','Ledger','Cash','Balance Sheet',self.doc.name,''],
					['Loans and Advances (Assets)','Current Assets','Group','','Balance Sheet',self.doc.name,''],
					['Securities and Deposits','Current Assets','Group','','Balance Sheet',self.doc.name,''],
						['Earnest Money','Securities and Deposits','Ledger','','Balance Sheet',self.doc.name,''],
					['Stock Assets','Current Assets','Group','Stock','Balance Sheet',self.doc.name,''],
					['Tax Assets','Current Assets','Group','','Balance Sheet',self.doc.name,''],
				['Fixed Assets','Application of Funds (Assets)','Group','','Balance Sheet',self.doc.name,''],
					['Capital Equipments','Fixed Assets','Ledger','Fixed Asset','Balance Sheet',self.doc.name,''],
					['Computers','Fixed Assets','Ledger','Fixed Asset','Balance Sheet',self.doc.name,''],
					['Furniture and Fixture','Fixed Assets','Ledger','Fixed Asset','Balance Sheet',self.doc.name,''],
					['Office Equipments','Fixed Assets','Ledger','Fixed Asset','Balance Sheet',self.doc.name,''],
					['Plant and Machinery','Fixed Assets','Ledger','Fixed Asset','Balance Sheet',self.doc.name,''],
				['Investments','Application of Funds (Assets)','Group','','Balance Sheet',self.doc.name,''],
				['Temporary Accounts (Assets)','Application of Funds (Assets)','Group','','Balance Sheet',self.doc.name,''],
					['Temporary Account (Assets)','Temporary Accounts (Assets)','Ledger','','Balance Sheet',self.doc.name,''],
			['Expenses','','Group','Expense Account','Profit and Loss',self.doc.name,''],
				['Direct Expenses','Expenses','Group','Expense Account','Profit and Loss',self.doc.name,''],
					['Stock Expenses','Direct Expenses','Group','Expense Account','Profit and Loss',self.doc.name,''],
						['Cost of Goods Sold','Stock Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
						['Stock Adjustment','Stock Expenses','Ledger','Stock Adjustment','Profit and Loss',self.doc.name,''],
						['Expenses Included In Valuation', "Stock Expenses", 'Ledger', 'Expenses Included In Valuation', 'Profit and Loss', self.doc.name, ''],
				['Indirect Expenses','Expenses','Group','Expense Account','Profit and Loss',self.doc.name,''],
					['Advertising and Publicity','Indirect Expenses','Ledger','Chargeable','Profit and Loss',self.doc.name,''],
					['Bad Debts Written Off','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Bank Charges','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Books and Periodicals','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Charity and Donations','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Commission on Sales','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Conveyance Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Customer Entertainment Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Depreciation Account','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Freight and Forwarding Charges','Indirect Expenses','Ledger','Chargeable','Profit and Loss',self.doc.name,''],
					['Legal Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Miscellaneous Expenses','Indirect Expenses','Ledger','Chargeable','Profit and Loss',self.doc.name,''],
					['Office Maintenance Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Office Rent','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Postal Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Print and Stationary','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Rounded Off','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Salary','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Sales Promotion Expenses','Indirect Expenses','Ledger','Chargeable','Profit and Loss',self.doc.name,''],
					['Service Charges Paid','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Staff Welfare Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Telephone Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Travelling Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
					['Water and Electricity Expenses','Indirect Expenses','Ledger','Expense Account','Profit and Loss',self.doc.name,''],
			['Income','','Group','','Profit and Loss',self.doc.name,''],
				['Direct Income','Income','Group','Income Account','Profit and Loss',self.doc.name,''],
					['Sales','Direct Income','Ledger','Income Account','Profit and Loss',self.doc.name,''],
					['Service','Direct Income','Ledger','Income Account','Profit and Loss',self.doc.name,''],
				['Indirect Income','Income','Group','Income Account','Profit and Loss',self.doc.name,''],
			['Source of Funds (Liabilities)','','Group','','Balance Sheet',self.doc.name,''],
				['Capital Account','Source of Funds (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
					['Reserves and Surplus','Capital Account','Ledger','','Balance Sheet',self.doc.name,''],
					['Shareholders Funds','Capital Account','Ledger','','Balance Sheet',self.doc.name,''],
				['Current Liabilities','Source of Funds (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
					['Accounts Payable','Current Liabilities','Group','','Balance Sheet',self.doc.name,''],
					['Stock Liabilities','Current Liabilities','Group','','Balance Sheet',self.doc.name,''],
						['Stock Received But Not Billed', 'Stock Liabilities', 'Ledger', 'Stock Received But Not Billed', 'Balance Sheet', self.doc.name, ''],					
					['Duties and Taxes','Current Liabilities','Group','','Balance Sheet',self.doc.name,''],
					['Loans (Liabilities)','Current Liabilities','Group','','Balance Sheet',self.doc.name,''],
						['Secured Loans','Loans (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
						['Unsecured Loans','Loans (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
						['Bank Overdraft Account','Loans (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
				['Temporary Accounts (Liabilities)','Source of Funds (Liabilities)','Group','','Balance Sheet',self.doc.name,''],
					['Temporary Account (Liabilities)','Temporary Accounts (Liabilities)','Ledger','','Balance Sheet',self.doc.name,'']
		]
		
		acc_list_india = [
			['CENVAT Capital Goods','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT Service Tax','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT Service Tax Cess 1','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT Service Tax Cess 2','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT Edu Cess','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['CENVAT SHE Cess','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['Excise Duty 4','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'4.00'],
			['Excise Duty 8','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'8.00'],
			['Excise Duty 10','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'10.00'],
			['Excise Duty 14','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'14.00'],
			['Excise Duty Edu Cess 2','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'2.00'],
			['Excise Duty SHE Cess 1','Tax Assets','Ledger','Tax','Balance Sheet',self.doc.name,'1.00'],
			['P L A','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['P L A - Cess Portion','Tax Assets','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['Edu. Cess on Excise','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'2.00'],
			['Edu. Cess on Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'2.00'],
			['Edu. Cess on TDS','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'2.00'],
			['Excise Duty @ 4','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'4.00'],
			['Excise Duty @ 8','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'8.00'],
			['Excise Duty @ 10','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'10.00'],
			['Excise Duty @ 14','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'14.00'],
			['Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'10.3'],
			['SHE Cess on Excise','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'1.00'],
			['SHE Cess on Service Tax','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'1.00'],
			['SHE Cess on TDS','Duties and Taxes','Ledger','Tax','Balance Sheet',self.doc.name,'1.00'],
			['Professional Tax','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['VAT','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Advertisement)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Commission)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Contractor)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Interest)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Rent)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,''],
			['TDS (Salary)','Duties and Taxes','Ledger','Chargeable','Balance Sheet',self.doc.name,'']
		 ]
		# load common account heads
		for d in acc_list_common:
			self.add_acc(d)

		country = frappe.db.sql("select value from tabSingles where field = 'country' and doctype = 'Control Panel'")
		country = country and cstr(country[0][0]) or ''

		# load taxes (only for India)
		if country == 'India':
			for d in acc_list_india:
				self.add_acc(d)

@frappe.whitelist()
def replace_abbr(company, old, new):
	frappe.db.set_value("Company", company, "abbr", new)
	
	def _rename_record(dt):
		for d in frappe.db.sql("select name from `tab%s` where company=%s" % (dt, '%s'), company):
			parts = d[0].split(" - ")
			if parts[-1].lower() == old.lower():
				name_without_abbr = " - ".join(parts[:-1])
				frappe.rename_doc(dt, d[0], name_without_abbr + " - " + new)
		
	for dt in ["Account", "Cost Center", "Warehouse"]:
		_rename_record(dt)
		frappe.db.commit()

def get_name_with_abbr(name, company):
	company_abbr = frappe.db.get_value("Company", company, "abbr")		
	parts = name.split(" - ")

	if parts[-1].lower() != company_abbr.lower():
		parts.append(company_abbr)
			
	return " - ".join(parts)
