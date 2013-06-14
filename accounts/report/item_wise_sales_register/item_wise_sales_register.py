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

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	item_list = get_items(filters)
	
	data = []
	for d in item_list:
		data.append([d.item_code, d.item_name, d.item_group, d.name, d.posting_date, d.customer, 
			d.debit_to, d.territory, d.project_name, d.company, d.sales_order, d.delivery_note,
			d.income_account, d.qty, d.basic_rate, d.amount])
	
	return columns, data
	
	
def get_columns():
	return [
		"Item Code:Link/Item:120", "Item Name::120", "Item Group:Link/Item Group:100", 
		"Invoice:Link/Sales Invoice:120", "Posting Date:Date:80", "Customer:Link/Customer:120", 
		"Customer Account:Link/Account:120", "Territory:Link/Territory:80",
		"Project:Link/Project:80", "Company:Link/Company:100", "Sales Order:Link/Sales Order:100", 
		"Delivery Note:Link/Delivery Note:100", "Income Account:Link/Account:140", 
		"Qty:Float:120", "Rate:Currency:120", "Amount:Currency:120"
	]
	
	
def get_conditions(filters):
	conditions = ""
	
	if filters.get("account"): conditions += " and si.debit_to = %(account)s"
	
	if filters.get("item_code"): conditions += " and si_item.item_code = %(item_code)s"

	if filters.get("from_date"): conditions += " and si.posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and si.posting_date<=%(to_date)s"

	return conditions
	
def get_items(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select si.name, si.posting_date, si.debit_to, si.project_name, 
		si.customer, si.remarks, si.territory, si.company, si_item.item_code, si_item.item_name, 
		si_item.item_group, si_item.sales_order, si_item.delivery_note, si_item.income_account, 
		si_item.qty, si_item.basic_rate, si_item.amount
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item 
		where si.name = si_item.parent and si.docstatus = 1 %s 
		order by si.posting_date desc, si_item.item_code desc""" % conditions, filters, as_dict=1)