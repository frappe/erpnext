# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)
	data = get_entries(filters)
	
	return columns, data
	
def get_columns(filters):
	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)
		
	return [filters["doc_type"] + ":Link/" + filters["doc_type"] + ":140", 
		"Customer:Link/Customer:140", "Territory:Link/Territory:100", "Posting Date:Date:100", 
		"Item Code:Link/Item:120", "Qty:Float:100", "Amount:Currency:120", 
		"Sales Person:Link/Sales Person:140", "Contribution %:Float:110", 
		"Contribution Amount:Currency:140"]
	
def get_entries(filters):
	date_field = filters["doc_type"] == "Sales Order" and "transaction_date" or "posting_date"
	conditions, items = get_conditions(filters, date_field)
	entries = webnotes.conn.sql("""select dt.name, dt.customer, dt.territory, dt.%s, 
		dt_item.item_code, dt_item.qty, dt_item.amount, st.sales_person, 
		st.allocated_percentage, dt_item.amount*st.allocated_percentage/100
		from `tab%s` dt, `tab%s Item` dt_item, `tabSales Team` st 
		where st.parent = dt.name and dt.name = dt_item.parent and st.parenttype = '%s' 
		and dt.docstatus = 1 %s order by st.sales_person, dt.name desc""" % 
		(date_field, filters["doc_type"], filters["doc_type"], filters["doc_type"], conditions), 
		tuple(items), as_list=1)
		
	return entries

def get_conditions(filters, date_field):
	conditions = ""
	if filters.get("company"): conditions += " and dt.company = '%s'" % filters["company"]
	if filters.get("customer"): conditions += " and dt.customer = '%s'" % filters["customer"]
	if filters.get("territory"): conditions += " and dt.territory = '%s'" % filters["territory"]
	
	if filters.get("from_date"): conditions += " and dt.%s >= '%s'" % \
		(date_field, filters["from_date"])
	if filters.get("to_date"): conditions += " and dt.%s <= '%s'" % (date_field, filters["to_date"])
	
	if filters.get("sales_person"): conditions += " and st.sales_person = '%s'" % \
	 	filters["sales_person"]
	
	items = get_items(filters)
	if items:
		conditions += " and dt_item.item_code in (%s)" % ', '.join(['%s']*len(items))
	
	return conditions, items

def get_items(filters):
	if filters.get("item_group"): key = "item_group"
	elif filters.get("brand"): key = "brand"
	else: key = ""

	items = []
	if key:
		items = webnotes.conn.sql_list("""select name from tabItem where %s = %s""" % 
			(key, '%s'), (filters[key]))
			
	return items