# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	last_col = len(columns)
	
	item_list = get_items(filters)
	aii_account_map = get_aii_accounts()
	item_tax, tax_accounts = get_tax_accounts(item_list, columns)
	
	data = []
	for d in item_list:
		expense_head = d.expense_head or aii_account_map.get(d.company)
		row = [d.item_code, d.item_name, d.item_group, d.parent, d.posting_date, 
			d.supplier_name, d.credit_to, d.project_name, d.company, d.purchase_order, 
			d.purchase_receipt, expense_head, d.qty, d.rate, d.amount]
		for tax in tax_accounts:
			row.append(item_tax.get(d.parent, {}).get(d.item_code, {}).get(tax, 0))

		total_tax = sum(row[last_col:])
		row += [total_tax, d.amount + total_tax]
		
		data.append(row)
	
	return columns, data
	
	
def get_columns():
	return ["Item Code:Link/Item:120", "Item Name::120", "Item Group:Link/Item Group:100", 
		"Invoice:Link/Purchase Invoice:120", "Posting Date:Date:80", "Supplier:Link/Customer:120", 
		"Supplier Account:Link/Account:120", "Project:Link/Project:80", "Company:Link/Company:100", 
		"Purchase Order:Link/Purchase Order:100", "Purchase Receipt:Link/Purchase Receipt:100", 
		"Expense Account:Link/Account:140", "Qty:Float:120", "Rate:Currency:120", 
		"Amount:Currency:120"]
	
def get_conditions(filters):
	conditions = ""
	
	for opts in (("company", " and company=%(company)s"),
		("account", " and pi.credit_to = %(account)s"),
		("item_code", " and pi_item.item_code = %(item_code)s"),
		("from_date", " and pi.posting_date>=%(from_date)s"),
		("to_date", " and pi.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions
	
def get_items(filters):
	conditions = get_conditions(filters)
	match_conditions = webnotes.build_match_conditions("Purchase Invoice")
	
	return webnotes.conn.sql("""select pi_item.parent, pi.posting_date, pi.credit_to, pi.company, 
		pi.supplier, pi.remarks, pi_item.item_code, pi_item.item_name, pi_item.item_group, 
		pi_item.project_name, pi_item.purchase_order, pi_item.purchase_receipt, 
		pi_item.expense_head, pi_item.qty, pi_item.rate, pi_item.amount, pi.supplier_name
		from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pi_item 
		where pi.name = pi_item.parent and pi.docstatus = 1 %s %s
		order by pi.posting_date desc, pi_item.item_code desc""" % (conditions, match_conditions), filters, as_dict=1)
		
def get_aii_accounts():
	return dict(webnotes.conn.sql("select name, stock_received_but_not_billed from tabCompany"))
	
def get_tax_accounts(item_list, columns):
	import json
	item_tax = {}
	tax_accounts = []
	
	tax_details = webnotes.conn.sql("""select parent, account_head, item_wise_tax_detail
		from `tabPurchase Taxes and Charges` where parenttype = 'Purchase Invoice' 
		and docstatus = 1 and ifnull(account_head, '') != '' and category in ('Total', 'Valuation and Total') 
		and parent in (%s)""" % ', '.join(['%s']*len(item_list)), tuple([item.parent for item in item_list]))
		
	for parent, account_head, item_wise_tax_detail in tax_details:
		if account_head not in tax_accounts:
			tax_accounts.append(account_head)
		
		if item_wise_tax_detail:
			try:
				item_wise_tax_detail = json.loads(item_wise_tax_detail)
				for item, tax_amount in item_wise_tax_detail.items():
					item_tax.setdefault(parent, {}).setdefault(item, {})[account_head] = \
						flt(tax_amount[1]) if isinstance(tax_amount, list) else flt(tax_amount)
				
			except ValueError:
				continue
	
	tax_accounts.sort()
	columns += [account_head + ":Currency:80" for account_head in tax_accounts]
	columns += ["Total Tax:Currency:80", "Total:Currency:80"]

	return item_tax, tax_accounts