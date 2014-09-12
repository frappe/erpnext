# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	invoice_list = get_invoices(filters)
	columns, expense_accounts, tax_accounts = get_columns(invoice_list)
	
	
	if not invoice_list:
		msgprint(_("No record found"))		
		return columns, invoice_list
	
	invoice_expense_map = get_invoice_expense_map(invoice_list)
	invoice_expense_map, invoice_tax_map = get_invoice_tax_map(invoice_list, 
		invoice_expense_map, expense_accounts)
	invoice_po_pr_map = get_invoice_po_pr_map(invoice_list)
	account_map = get_account_details(invoice_list)

	data = []
	for inv in invoice_list:
		# invoice details
		purchase_order = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_order", [])))
		purchase_receipt = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_receipt", [])))
		project_name = list(set(invoice_po_pr_map.get(inv.name, {}).get("project_name", [])))

		row = [inv.name, inv.posting_date, inv.supplier, inv.supplier_name, inv.credit_to, 
			account_map.get(inv.credit_to), ", ".join(project_name), inv.bill_no, inv.bill_date, 
			inv.remarks, ", ".join(purchase_order), ", ".join(purchase_receipt)]
		
		# map expense values
		net_total = 0
		for expense_acc in expense_accounts:
			expense_amount = flt(invoice_expense_map.get(inv.name, {}).get(expense_acc))
			net_total += expense_amount
			row.append(expense_amount)
		
		# net total
		row.append(net_total or inv.net_total)
			
		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in expense_accounts:
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc))
				total_tax += tax_amount
				row.append(tax_amount)

		# total tax, grand total, outstanding amount & rounded total
		row += [total_tax, inv.grand_total, flt(inv.grand_total, 2), inv.outstanding_amount]
		data.append(row)
		# raise Exception
	
	return columns, data
	
	
def get_columns(invoice_list):
	"""return columns based on filters"""
	columns = [
		_("Invoice") + ":Link/Purchase Invoice:120", _("Posting Date") + ":Date:80", _("Supplier Id") + "::120", 
		_("Supplier Name") + "::120", _("Supplier Account") + ":Link/Account:120", 
		_("Account Group") + ":Link/Account:120", _("Project") + ":Link/Project:80", _("Bill No") + "::120", 
		_("Bill Date") + ":Date:80", _("Remarks") + "::150", 
		_("Purchase Order") + ":Link/Purchase Order:100", _("Purchase Receipt") + ":Link/Purchase Receipt:100"
	]
	expense_accounts = tax_accounts = expense_columns = tax_columns = []
	
	if invoice_list:	
		expense_accounts = frappe.db.sql_list("""select distinct expense_account 
			from `tabPurchase Invoice Item` where docstatus = 1 and ifnull(expense_account, '') != '' 
			and parent in (%s) order by expense_account""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))
		
		tax_accounts = 	frappe.db.sql_list("""select distinct account_head 
			from `tabPurchase Taxes and Charges` where parenttype = 'Purchase Invoice' 
			and docstatus = 1 and ifnull(account_head, '') != '' and category in ('Total', 'Valuation and Total') 
			and parent in (%s) order by account_head""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))
			
				
	expense_columns = [(account + ":Currency:120") for account in expense_accounts]
	for account in tax_accounts:
		if account not in expense_accounts:
			tax_columns.append(account + ":Currency:120")
	
	columns = columns + expense_columns + \
		["Net Total:Currency:120"] + tax_columns + \
		["Total Tax:Currency:120"] + ["Grand Total:Currency:120"] + \
		["Rounded Total:Currency:120"] + ["Outstanding Amount:Currency:120"]

	return columns, expense_accounts, tax_accounts

def get_conditions(filters):
	conditions = ""
	
	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("account"): conditions += " and credit_to = %(account)s"

	if filters.get("from_date"): conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date<=%(to_date)s"

	return conditions
	
def get_invoices(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, posting_date, credit_to, supplier, supplier_name, 
		bill_no, bill_date, remarks, net_total, grand_total, outstanding_amount 
		from `tabPurchase Invoice` where docstatus = 1 %s 
		order by posting_date desc, name desc""" % conditions, filters, as_dict=1)
	
	
def get_invoice_expense_map(invoice_list):
	expense_details = frappe.db.sql("""select parent, expense_account, sum(base_amount) as amount
		from `tabPurchase Invoice Item` where parent in (%s) group by parent, expense_account""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_expense_map = {}
	for d in expense_details:
		invoice_expense_map.setdefault(d.parent, frappe._dict()).setdefault(d.expense_account, [])
		invoice_expense_map[d.parent][d.expense_account] = flt(d.amount)
	
	return invoice_expense_map
	
def get_invoice_tax_map(invoice_list, invoice_expense_map, expense_accounts):
	tax_details = frappe.db.sql("""select parent, account_head, sum(tax_amount) as tax_amount
		from `tabPurchase Taxes and Charges` where parent in (%s) group by parent, account_head""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_tax_map = {}
	for d in tax_details:
		if d.account_head in expense_accounts:
			if invoice_expense_map[d.parent].has_key(d.account_head):
				invoice_expense_map[d.parent][d.account_head] += flt(d.tax_amount)
			else:
				invoice_expense_map[d.parent][d.account_head] = flt(d.tax_amount)
		else:
			invoice_tax_map.setdefault(d.parent, frappe._dict()).setdefault(d.account_head, [])
			invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)
	
	return invoice_expense_map, invoice_tax_map
	
def get_invoice_po_pr_map(invoice_list):
	pi_items = frappe.db.sql("""select parent, purchase_order, purchase_receipt, 
		project_name from `tabPurchase Invoice Item` where parent in (%s) 
		and (ifnull(purchase_order, '') != '' or ifnull(purchase_receipt, '') != '')""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_po_pr_map = {}
	for d in pi_items:
		if d.purchase_order:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault(
				"purchase_order", []).append(d.purchase_order)
		if d.purchase_receipt:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault(
				"purchase_receipt", []).append(d.purchase_receipt)
		if d.project_name:
			invoice_po_pr_map.setdefault(d.parent, frappe._dict()).setdefault(
				"project_name", []).append(d.project_name)
				
	return invoice_po_pr_map
	
def get_account_details(invoice_list):
	account_map = {}
	accounts = list(set([inv.credit_to for inv in invoice_list]))
	for acc in frappe.db.sql("""select name, parent_account from tabAccount 
		where name in (%s)""" % ", ".join(["%s"]*len(accounts)), tuple(accounts), as_dict=1):
			account_map[acc.name] = acc.parent_account
						
	return account_map