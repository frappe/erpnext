# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	
	invoice_list = get_invoices(filters)
	columns, income_accounts, tax_accounts = get_columns(invoice_list)
	
	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list
	
	invoice_income_map = get_invoice_income_map(invoice_list)
	invoice_income_map, invoice_tax_map = get_invoice_tax_map(invoice_list, 
		invoice_income_map, income_accounts)
	
	invoice_so_dn_map = get_invoice_so_dn_map(invoice_list)
	customer_map = get_customer_deatils(invoice_list)
	account_map = get_account_details(invoice_list)

	data = []
	for inv in invoice_list:
		# invoice details
		sales_order = list(set(invoice_so_dn_map.get(inv.name, {}).get("sales_order", [])))
		delivery_note = list(set(invoice_so_dn_map.get(inv.name, {}).get("delivery_note", [])))

		row = [inv.name, inv.posting_date, inv.customer, inv.customer_name, inv.debit_to, 
			account_map.get(inv.debit_to), customer_map.get(inv.customer), inv.project_name, 
			inv.remarks, ", ".join(sales_order), ", ".join(delivery_note)]
		
		# map income values
		net_total = 0
		for income_acc in income_accounts:
			income_amount = flt(invoice_income_map.get(inv.name, {}).get(income_acc))
			net_total += income_amount
			row.append(income_amount)
		
		# net total
		row.append(net_total or inv.net_total)
			
		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in income_accounts:
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc))
				total_tax += tax_amount
				row.append(tax_amount)

		# total tax, grand total, outstanding amount & rounded total
		row += [total_tax, inv.grand_total, inv.rounded_total, inv.outstanding_amount]

		data.append(row)
	
	return columns, data
	
	
def get_columns(invoice_list):
	"""return columns based on filters"""
	columns = [
		_("Invoice") + ":Link/Sales Invoice:120", _("Posting Date") + ":Date:80", _("Customer Id") + "::120", 
		_("Customer Name") + "::120", _("Customer Account") + ":Link/Account:120", _("Account Group") + ":Link/Account:120",
		_("Territory") + ":Link/Territory:80", _("Project") + ":Link/Project:80", _("Remarks") + "::150", 
		_("Sales Order") + ":Link/Sales Order:100", _("Delivery Note") + ":Link/Delivery Note:100"
	]
	
	income_accounts = tax_accounts = income_columns = tax_columns = []
	
	if invoice_list:
		income_accounts = frappe.db.sql_list("""select distinct income_account 
			from `tabSales Invoice Item` where docstatus = 1 and parent in (%s) 
			order by income_account""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))
	
		tax_accounts = 	frappe.db.sql_list("""select distinct account_head 
			from `tabSales Taxes and Charges` where parenttype = 'Sales Invoice' 
			and docstatus = 1 and ifnull(tax_amount_after_discount_amount, 0) != 0 
			and parent in (%s) order by account_head""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))

	income_columns = [(account + ":Currency:120") for account in income_accounts]
	for account in tax_accounts:
		if account not in income_accounts:
			tax_columns.append(account + ":Currency:120")
	
	columns = columns + income_columns + ["Net Total:Currency:120"] + tax_columns + \
		["Total Tax:Currency:120"] + ["Grand Total:Currency:120"] + \
		["Rounded Total:Currency:120"] + ["Outstanding Amount:Currency:120"]

	return columns, income_accounts, tax_accounts

def get_conditions(filters):
	conditions = ""
	
	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("account"): conditions += " and debit_to = %(account)s"

	if filters.get("from_date"): conditions += " and posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date <= %(to_date)s"

	return conditions
	
def get_invoices(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, posting_date, debit_to, project_name, customer, 
		customer_name, remarks, net_total, grand_total, rounded_total, outstanding_amount 
		from `tabSales Invoice` 
		where docstatus = 1 %s order by posting_date desc, name desc""" % 
		conditions, filters, as_dict=1)
	
def get_invoice_income_map(invoice_list):
	income_details = frappe.db.sql("""select parent, income_account, sum(base_amount) as amount
		from `tabSales Invoice Item` where parent in (%s) group by parent, income_account""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_income_map = {}
	for d in income_details:
		invoice_income_map.setdefault(d.parent, frappe._dict()).setdefault(d.income_account, [])
		invoice_income_map[d.parent][d.income_account] = flt(d.amount)
	
	return invoice_income_map
	
def get_invoice_tax_map(invoice_list, invoice_income_map, income_accounts):
	tax_details = frappe.db.sql("""select parent, account_head, 
		sum(tax_amount_after_discount_amount) as tax_amount 
		from `tabSales Taxes and Charges` where parent in (%s) group by parent, account_head""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_tax_map = {}
	for d in tax_details:
		if d.account_head in income_accounts:
			if invoice_income_map[d.parent].has_key(d.account_head):
				invoice_income_map[d.parent][d.account_head] += flt(d.tax_amount)
			else:
				invoice_income_map[d.parent][d.account_head] = flt(d.tax_amount)
		else:
			invoice_tax_map.setdefault(d.parent, frappe._dict()).setdefault(d.account_head, [])
			invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)
	
	return invoice_income_map, invoice_tax_map
	
def get_invoice_so_dn_map(invoice_list):
	si_items = frappe.db.sql("""select parent, sales_order, delivery_note
		from `tabSales Invoice Item` where parent in (%s) 
		and (ifnull(sales_order, '') != '' or ifnull(delivery_note, '') != '')""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_so_dn_map = {}
	for d in si_items:
		if d.sales_order:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault(
				"sales_order", []).append(d.sales_order)
		if d.delivery_note:
			invoice_so_dn_map.setdefault(d.parent, frappe._dict()).setdefault(
				"delivery_note", []).append(d.delivery_note)
				
	return invoice_so_dn_map
	
def get_customer_deatils(invoice_list):
	customer_map = {}
	customers = list(set([inv.customer for inv in invoice_list]))
	for cust in frappe.db.sql("""select name, territory from `tabCustomer` 
		where name in (%s)""" % ", ".join(["%s"]*len(customers)), tuple(customers), as_dict=1):
			customer_map[cust.name] = cust.territory
	
	return customer_map
	
def get_account_details(invoice_list):
	account_map = {}
	accounts = list(set([inv.debit_to for inv in invoice_list]))
	for acc in frappe.db.sql("""select name, parent_account from tabAccount 
		where name in (%s)""" % ", ".join(["%s"]*len(accounts)), tuple(accounts), as_dict=1):
			account_map[acc.name] = acc.parent_account
						
	return account_map