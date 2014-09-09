# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, os
from frappe import _

from frappe.utils import cint
import frappe.defaults


from frappe.model.document import Document

class Company(Document):
	def onload(self):
		self.get("__onload").transactions_exist = self.check_if_transactions_exist()

	def check_if_transactions_exist(self):
		exists = False
		for doctype in ["Sales Invoice", "Delivery Note", "Sales Order", "Quotation",
			"Purchase Invoice", "Purchase Receipt", "Purchase Order", "Supplier Quotation"]:
				if frappe.db.sql("""select name from `tab%s` where company=%s and docstatus=1
					limit 1""" % (doctype, "%s"), self.name):
						exists = True
						break

		return exists

	def validate(self):
		if self.get('__islocal') and len(self.abbr) > 5:
			frappe.throw(_("Abbreviation cannot have more than 5 characters"))

		self.previous_default_currency = frappe.db.get_value("Company", self.name, "default_currency")
		if self.default_currency and self.previous_default_currency and \
			self.default_currency != self.previous_default_currency and \
			self.check_if_transactions_exist():
				frappe.throw(_("Cannot change company's default currency, because there are existing transactions. Transactions must be cancelled to change the default currency."))

		self.validate_default_accounts()

	def validate_default_accounts(self):
		for field in ["default_bank_account", "default_cash_account", "receivables_group", "payables_group",
			"default_expense_account", "default_income_account", "stock_received_but_not_billed",
			"stock_adjustment_account", "expenses_included_in_valuation"]:
				if self.get(field):
					for_company = frappe.db.get_value("Account", self.get(field), "company")
					if for_company != self.name:
						frappe.throw(_("Account {0} does not belong to company: {1}")
							.format(self.get(field), self.name))

	def on_update(self):
		if not frappe.db.sql("""select name from tabAccount
			where company=%s and docstatus<2 limit 1""", self.name):
			self.create_default_accounts()
			self.create_default_warehouses()
			self.install_country_fixtures()

		if not frappe.db.get_value("Cost Center", {"group_or_ledger": "Ledger",
				"company": self.name}):
			self.create_default_cost_center()

		self.set_default_accounts()

		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

	def install_country_fixtures(self):
		if os.path.exists(os.path.join(os.path.dirname(__file__), "fixtures", self.country.lower())):
			frappe.get_attr("erpnext.setup.doctype.company.fixtures.{0}.install".format(self.country.lower()))(self)

	def create_default_warehouses(self):
		for whname in (_("Stores"), _("Work In Progress"), _("Finished Goods")):
			if not frappe.db.exists("Warehouse", whname + " - " + self.abbr):
				stock_group = frappe.db.get_value("Account", {"account_type": "Stock",
					"group_or_ledger": "Group", "company": self.name})
				if stock_group:
					frappe.get_doc({
						"doctype":"Warehouse",
						"warehouse_name": whname,
						"company": self.name,
						"create_account_under": stock_group
					}).insert()

	def create_default_accounts(self):
		if self.chart_of_accounts:
			self.import_chart_of_account()
		else:
			self.create_standard_accounts()
			frappe.db.set(self, "receivables_group", _("Accounts Receivable") + " - " + self.abbr)
			frappe.db.set(self, "payables_group", _("Accounts Payable") + " - " + self.abbr)

	def import_chart_of_account(self):
		chart = frappe.get_doc("Chart of Accounts", self.chart_of_accounts)
		chart.create_accounts(self.name)

	def add_acc(self, lst):
		account = frappe.get_doc({
			"doctype": "Account",
			"freeze_account": "No",
			"master_type": "",
			"company": self.name
		})

		for d in self.fld_dict.keys():
			account.set(d, (d == 'parent_account' and lst[self.fld_dict[d]]) and lst[self.fld_dict[d]] +' - '+ self.abbr or lst[self.fld_dict[d]])
		if not account.parent_account:
			account.ignore_mandatory = True
		account.insert()

	def set_default_accounts(self):
		def _set_default_account(fieldname, account_type):
			if self.get(fieldname):
				return

			account = frappe.db.get_value("Account", {"account_type": account_type,
				"group_or_ledger": "Ledger", "company": self.name})

			if account:
				self.db_set(fieldname, account)

		_set_default_account("default_cash_account", "Cash")
		_set_default_account("default_bank_account", "Bank")

		if cint(frappe.db.get_value("Accounts Settings", None, "auto_accounting_for_stock")):
			_set_default_account("stock_received_but_not_billed", "Stock Received But Not Billed")
			_set_default_account("stock_adjustment_account", "Stock Adjustment")
			_set_default_account("expenses_included_in_valuation", "Expenses Included In Valuation")

		if not self.default_income_account:
			self.db_set("default_income_account", frappe.db.get_value("Account",
				{"account_name": _("Sales"), "company": self.name}))

	def create_default_cost_center(self):
		cc_list = [
			{
				'cost_center_name': self.name,
				'company':self.name,
				'group_or_ledger':'Group',
				'parent_cost_center':None
			},
			{
				'cost_center_name':_('Main'),
				'company':self.name,
				'group_or_ledger':'Ledger',
				'parent_cost_center':self.name + ' - ' + self.abbr
			},
		]
		for cc in cc_list:
			cc.update({"doctype": "Cost Center"})
			cc_doc = frappe.get_doc(cc)
			cc_doc.ignore_permissions = True

			if cc.get("cost_center_name") == self.name:
				cc_doc.ignore_mandatory = True
			cc_doc.insert()

		frappe.db.set(self, "cost_center", _("Main") + " - " + self.abbr)

	def on_trash(self):
		"""
			Trash accounts and cost centers for this company if no gl entry exists
		"""
		rec = frappe.db.sql("SELECT name from `tabGL Entry` where company = %s", self.name)
		if not rec:
			#delete tabAccount
			frappe.db.sql("delete from `tabAccount` where company = %s order by lft desc, rgt desc", self.name)

			#delete cost center child table - budget detail
			frappe.db.sql("delete bd.* from `tabBudget Detail` bd, `tabCost Center` cc where bd.parent = cc.name and cc.company = %s", self.name)
			#delete cost center
			frappe.db.sql("delete from `tabCost Center` WHERE company = %s order by lft desc, rgt desc", self.name)

		if not frappe.db.get_value("Stock Ledger Entry", {"company": self.name}):
			frappe.db.sql("""delete from `tabWarehouse` where company=%s""", self.name)

		frappe.defaults.clear_default("company", value=self.name)

		frappe.db.sql("""update `tabSingles` set value=""
			where doctype='Global Defaults' and field='default_company'
			and value=%s""", self.name)

	def before_rename(self, olddn, newdn, merge=False):
		if merge:
			frappe.throw(_("Sorry, companies cannot be merged"))

	def after_rename(self, olddn, newdn, merge=False):
		frappe.db.set(self, "company_name", newdn)

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
			'tax_rate': 5,
			'root_type': 6
		}

		acc_list_common = [
			[_('Application of Funds (Assets)'), None,'Group', None,'Balance Sheet', None, 'Asset'],
				[_('Current Assets'),_('Application of Funds (Assets)'),'Group', None,'Balance Sheet', None, 'Asset'],
					[_('Accounts Receivable'),_('Current Assets'),'Group', None,'Balance Sheet', None, 'Asset'],
					[_('Bank Accounts'),_('Current Assets'),'Group','Bank','Balance Sheet', None, 'Asset'],
					[_('Cash In Hand'),_('Current Assets'),'Group','Cash','Balance Sheet', None, 'Asset'],
						[_('Cash'),_('Cash In Hand'),'Ledger','Cash','Balance Sheet', None, 'Asset'],
					[_('Loans and Advances (Assets)'),_('Current Assets'),'Group', None,'Balance Sheet', None, 'Asset'],
					[_('Securities and Deposits'),_('Current Assets'),'Group', None,'Balance Sheet', None, 'Asset'],
						[_('Earnest Money'),_('Securities and Deposits'),'Ledger', None,'Balance Sheet', None, 'Asset'],
					[_('Stock Assets'),_('Current Assets'),'Group','Stock','Balance Sheet', None, 'Asset'],
					[_('Tax Assets'),_('Current Assets'),'Group', None,'Balance Sheet', None, 'Asset'],
				[_('Fixed Assets'),_('Application of Funds (Assets)'),'Group', None,'Balance Sheet', None, 'Asset'],
					[_('Capital Equipments'),_('Fixed Assets'),'Ledger','Fixed Asset','Balance Sheet', None, 'Asset'],
					[_('Computers'),_('Fixed Assets'),'Ledger','Fixed Asset','Balance Sheet', None, 'Asset'],
					[_('Furniture and Fixture'),_('Fixed Assets'),'Ledger','Fixed Asset','Balance Sheet', None, 'Asset'],
					[_('Office Equipments'),_('Fixed Assets'),'Ledger','Fixed Asset','Balance Sheet', None, 'Asset'],
					[_('Plant and Machinery'),_('Fixed Assets'),'Ledger','Fixed Asset','Balance Sheet', None, 'Asset'],
				[_('Investments'),_('Application of Funds (Assets)'),'Group', None,'Balance Sheet', None, 'Asset'],
				[_('Temporary Accounts (Assets)'),_('Application of Funds (Assets)'),'Group', None,'Balance Sheet', None, 'Asset'],
					[_('Temporary Assets'),_('Temporary Accounts (Assets)'),'Ledger', None,'Balance Sheet', None, 'Asset'],
			[_('Expenses'), None,'Group','Expense Account','Profit and Loss', None, 'Expense'],
				[_('Direct Expenses'),_('Expenses'),'Group','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Stock Expenses'),_('Direct Expenses'),'Group','Expense Account','Profit and Loss', None, 'Expense'],
						[_('Cost of Goods Sold'),_('Stock Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
						[_('Stock Adjustment'),_('Stock Expenses'),'Ledger','Stock Adjustment','Profit and Loss', None, 'Expense'],
						[_('Expenses Included In Valuation'), _("Stock Expenses"), 'Ledger', 'Expenses Included In Valuation', 'Profit and Loss',  None, 'Expense'],
				[_('Indirect Expenses'), _('Expenses'),'Group','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Marketing Expenses'), _('Indirect Expenses'),'Ledger','Chargeable','Profit and Loss', None, 'Expense'],
					[_('Sales Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Administrative Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Charity and Donations'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Commission on Sales'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Travel Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Entertainment Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Depreciation'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Freight and Forwarding Charges'), _('Indirect Expenses'),'Ledger','Chargeable','Profit and Loss', None, 'Expense'],
					[_('Legal Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Miscellaneous Expenses'), _('Indirect Expenses'),'Ledger','Chargeable','Profit and Loss', None, 'Expense'],
					[_('Office Maintenance Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Office Rent'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Postal Expenses'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Print and Stationary'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Rounded Off'), _('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Salary') ,_('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Telephone Expenses') ,_('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
					[_('Utility Expenses') ,_('Indirect Expenses'),'Ledger','Expense Account','Profit and Loss', None, 'Expense'],
			[_('Income'), None,'Group', None,'Profit and Loss', None, 'Income'],
				[_('Direct Income'),_('Income'),'Group','Income Account','Profit and Loss', None, 'Income'],
					[_('Sales'),_('Direct Income'),'Ledger','Income Account','Profit and Loss', None, 'Income'],
					[_('Service'),_('Direct Income'),'Ledger','Income Account','Profit and Loss', None, 'Income'],
				[_('Indirect Income'),_('Income'),'Group','Income Account','Profit and Loss', None, 'Income'],
			[_('Source of Funds (Liabilities)'), None,'Group', None,'Balance Sheet', None, 'Liability'],
				[_('Capital Account'),_('Source of Funds (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
					[_('Reserves and Surplus'),_('Capital Account'),'Ledger', None,'Balance Sheet', None, 'Liability'],
					[_('Shareholders Funds'),_('Capital Account'),'Ledger', None,'Balance Sheet', None, 'Liability'],
				[_('Current Liabilities'),_('Source of Funds (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
					[_('Accounts Payable'),_('Current Liabilities'),'Group', None,'Balance Sheet', None, 'Liability'],
					[_('Stock Liabilities'),_('Current Liabilities'),'Group', None,'Balance Sheet', None, 'Liability'],
						[_('Stock Received But Not Billed'), _('Stock Liabilities'), 'Ledger', 'Stock Received But Not Billed', 'Balance Sheet',  None, 'Liability'],
					[_('Duties and Taxes'),_('Current Liabilities'),'Group', None,'Balance Sheet', None, 'Liability'],
					[_('Loans (Liabilities)'),_('Current Liabilities'),'Group', None,'Balance Sheet', None, 'Liability'],
						[_('Secured Loans'),_('Loans (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
						[_('Unsecured Loans'),_('Loans (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
						[_('Bank Overdraft Account'),_('Loans (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
				[_('Temporary Accounts (Liabilities)'),_('Source of Funds (Liabilities)'),'Group', None,'Balance Sheet', None, 'Liability'],
					[_('Temporary Liabilities'),_('Temporary Accounts (Liabilities)'),'Ledger', None,'Balance Sheet', None, 'Liability']
		]

		# load common account heads
		for d in acc_list_common:
			self.add_acc(d)

@frappe.whitelist()
def replace_abbr(company, old, new):
	frappe.only_for("System Manager")

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
