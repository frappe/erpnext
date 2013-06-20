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

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	item_list = get_items(filters)
	aii_account_map = get_aii_accounts()
	data = []
	for d in item_list:
		expense_head = d.expense_head or aii_account_map.get(d.company)
		data.append([d.item_code, d.item_name, d.item_group, d.name, d.posting_date, d.supplier, 
			d.credit_to, d.project_name, d.company, d.purchase_order, d.purchase_receipt,
			expense_head, d.qty, d.rate, d.amount])
	
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
	
	if filters.get("account"): conditions += " and pi.credit_to = %(account)s"
	
	if filters.get("item_code"): conditions += " and pi_item.item_code = %(item_code)s"

	if filters.get("from_date"): conditions += " and pi.posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and pi.posting_date<=%(to_date)s"

	return conditions
	
def get_items(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select pi.name, pi.posting_date, pi.credit_to, pi.company, 
		pi.supplier, pi.remarks, pi_item.item_code, pi_item.item_name, pi_item.item_group, 
		pi_item.project_name, pi_item.purchase_order, pi_item.purchase_receipt, 
		pi_item.expense_head, pi_item.qty, pi_item.rate, pi_item.amount
		from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pi_item 
		where pi.name = pi_item.parent and pi.docstatus = 1 %s 
		order by pi.posting_date desc, pi_item.item_code desc""" % conditions, filters, as_dict=1)
		
def get_aii_accounts():
	aii_account_map = {}
	for d in webnotes.conn.sql("select name, stock_received_but_not_billed from tabCompany",
	 		as_dict=1):
		aii_account_map.setdefault(d.name, d.stock_received_but_not_billed)
		
	return aii_account_map