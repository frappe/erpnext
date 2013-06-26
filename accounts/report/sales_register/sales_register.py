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
from webnotes.utils import flt
from webnotes import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	
	invoice_list = get_invoices(filters)
	columns, income_accounts, tax_accounts = get_columns(invoice_list)
	
	if not invoice_list:
		msgprint(_("No record found"))		
		return columns, invoice_list
	
	invoice_income_map = get_invoice_income_map(invoice_list)
	invoice_tax_map = get_invoice_tax_map(invoice_list)
	
	invoice_so_dn_map = get_invoice_so_dn_map(invoice_list)
	customer_map = get_customer_deatils(invoice_list)
	account_map = get_account_details(invoice_list)

	data = []
	for inv in invoice_list:
		# invoice details
		sales_order = list(set(invoice_so_dn_map.get(inv.name, {}).get("sales_order", [])))
		delivery_note = list(set(invoice_so_dn_map.get(inv.name, {}).get("delivery_note", [])))

		row = [inv.name, inv.posting_date, inv.customer, inv.debit_to, 
			account_map.get(inv.debit_to), customer_map.get(inv.customer), inv.project_name, 
			inv.remarks, ", ".join(sales_order), ", ".join(delivery_note)]
		
		# map income values
		for income_acc in income_accounts:
			row.append(invoice_income_map.get(inv.name, {}).get(income_acc))
		
		# net total
		row.append(inv.net_total)
			
		# tax account
		for tax_acc in tax_accounts:
			row.append(invoice_tax_map.get(inv.name, {}).get(tax_acc))

		# total tax, grand total, outstanding amount & rounded total
		row += [inv.other_charges_total, inv.grand_total, inv.rounded_total, inv.outstanding_amount]

		data.append(row)
	
	return columns, data
	
	
def get_columns(invoice_list):
	"""return columns based on filters"""
	columns = [
		"Invoice:Link/Sales Invoice:120", "Posting Date:Date:80", "Customer:Link/Customer:120", 
		"Customer Account:Link/Account:120", "Account Group:LInk/Account:120",
		"Territory:Link/Territory:80", "Project:Link/Project:80", 
		"Remarks::150", "Sales Order:Link/Sales Order:100", "Delivery Note:Link/Delivery Note:100"
	]
	
	income_accounts = tax_accounts = []
	if invoice_list:
		income_accounts = webnotes.conn.sql_list("""select distinct income_account 
			from `tabSales Invoice Item` where docstatus = 1 and parent in (%s) 
			order by income_account""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))
	
		tax_accounts = 	webnotes.conn.sql_list("""select distinct account_head 
			from `tabSales Taxes and Charges` where parenttype = 'Sales Invoice' 
			and docstatus = 1 and parent in (%s) order by account_head""" % 
			', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]))
	
	columns = columns + [(account + ":Currency:120") for account in income_accounts] + \
		["Net Total:Currency:120"] + [(account + ":Currency:120") for account in tax_accounts] + \
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
	return webnotes.conn.sql("""select name, posting_date, debit_to, project_name, customer, 
		remarks, net_total, other_charges_total, grand_total, rounded_total, 
		outstanding_amount from `tabSales Invoice` 
		where docstatus = 1 %s order by posting_date desc, name desc""" % 
		conditions, filters, as_dict=1)
	
def get_invoice_income_map(invoice_list):
	income_details = webnotes.conn.sql("""select parent, income_account, sum(amount) as amount
		from `tabSales Invoice Item` where parent in (%s) group by parent, income_account""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_income_map = {}
	for d in income_details:
		invoice_income_map.setdefault(d.parent, webnotes._dict()).setdefault(d.income_account, [])
		invoice_income_map[d.parent][d.income_account] = flt(d.amount)
	
	return invoice_income_map
	
def get_invoice_tax_map(invoice_list):
	tax_details = webnotes.conn.sql("""select parent, account_head, sum(tax_amount) as tax_amount
		from `tabSales Taxes and Charges` where parent in (%s) group by parent, account_head""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_tax_map = {}
	for d in tax_details:
		invoice_tax_map.setdefault(d.parent, webnotes._dict()).setdefault(d.account_head, [])
		invoice_tax_map[d.parent][d.account_head] = flt(d.tax_amount)
	
	return invoice_tax_map
	
def get_invoice_so_dn_map(invoice_list):
	si_items = webnotes.conn.sql("""select parent, sales_order, delivery_note
		from `tabSales Invoice Item` where parent in (%s) 
		and (ifnull(sales_order, '') != '' or ifnull(delivery_note, '') != '')""" % 
		', '.join(['%s']*len(invoice_list)), tuple([inv.name for inv in invoice_list]), as_dict=1)
	
	invoice_so_dn_map = {}
	for d in si_items:
		if d.sales_order:
			invoice_so_dn_map.setdefault(d.parent, webnotes._dict()).setdefault(
				"sales_order", []).append(d.sales_order)
		if d.delivery_note:
			invoice_so_dn_map.setdefault(d.parent, webnotes._dict()).setdefault(
				"delivery_note", []).append(d.delivery_note)
				
	return invoice_so_dn_map
	
def get_customer_deatils(invoice_list):
	customer_map = {}
	customers = list(set([inv.customer for inv in invoice_list]))
	for cust in webnotes.conn.sql("""select name, territory from `tabCustomer` 
		where name in (%s)""" % ", ".join(["%s"]*len(customers)), tuple(customers), as_dict=1):
			customer_map[cust.name] = cust.territory
	
	return customer_map
	
def get_account_details(invoice_list):
	account_map = {}
	accounts = list(set([inv.debit_to for inv in invoice_list]))
	for acc in webnotes.conn.sql("""select name, parent_account from tabAccount 
		where name in (%s)""" % ", ".join(["%s"]*len(accounts)), tuple(accounts), as_dict=1):
			account_map[acc.name] = acc.parent_account
						
	return account_map