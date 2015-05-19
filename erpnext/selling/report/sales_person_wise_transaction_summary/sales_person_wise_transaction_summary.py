# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	entries = get_entries(filters)
	item_details = get_item_details()
	data = []
	for d in entries:
		data.append([
			d.name, d.customer, d.territory, d.posting_date, d.item_code,
			item_details.get(d.item_code, {}).get("item_group"), item_details.get(d.item_code, {}).get("brand"),
			d.qty, d.base_net_amount, d.sales_person, d.allocated_percentage, d.contribution_amt
		])

	return columns, data

def get_columns(filters):
	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	return [filters["doc_type"] + ":Link/" + filters["doc_type"] + ":140",
		_("Customer") + ":Link/Customer:140", _("Territory") + ":Link/Territory:100", _("Posting Date") + ":Date:100",
		_("Item Code") + ":Link/Item:120", _("Item Group") + ":Link/Item Group:120",
		_("Brand") + ":Link/Brand:120", _("Qty") + ":Float:100", _("Amount") + ":Currency:120",
		_("Sales Person") + ":Link/Sales Person:140", _("Contribution %") + ":Float:110",
		_("Contribution Amount") + ":Currency:140"]

def get_entries(filters):
	date_field = filters["doc_type"] == "Sales Order" and "transaction_date" or "posting_date"
	conditions, items = get_conditions(filters, date_field)
	entries = frappe.db.sql("""select dt.name, dt.customer, dt.territory, dt.%s as posting_date,
		dt_item.item_code, dt_item.qty, dt_item.base_net_amount, st.sales_person,
		st.allocated_percentage, dt_item.base_net_amount*st.allocated_percentage/100 as contribution_amt
		from `tab%s` dt, `tab%s Item` dt_item, `tabSales Team` st
		where st.parent = dt.name and dt.name = dt_item.parent and st.parenttype = %s
		and dt.docstatus = 1 %s order by st.sales_person, dt.name desc""" %
		(date_field, filters["doc_type"], filters["doc_type"], '%s', conditions),
		tuple([filters["doc_type"]] + items), as_dict=1)

	return entries

def get_conditions(filters, date_field):
	conditions = ""
	if filters.get("company"): conditions += " and dt.company = '%s'" % \
		filters["company"].replace("'", "\'")
	if filters.get("customer"): conditions += " and dt.customer = '%s'" % \
		filters["customer"].replace("'", "\'")
	if filters.get("territory"): conditions += " and dt.territory = '%s'" % \
		filters["territory"].replace("'", "\'")

	if filters.get("from_date"): conditions += " and dt.%s >= '%s'" % \
		(date_field, filters["from_date"])
	if filters.get("to_date"): conditions += " and dt.%s <= '%s'" % (date_field, filters["to_date"])

	if filters.get("sales_person"): conditions += " and st.sales_person = '%s'" % \
	 	filters["sales_person"].replace("'", "\'")

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
		items = frappe.db.sql_list("""select name from tabItem where %s = %s""" %
			(key, '%s'), (filters[key]))

	return items

def get_item_details():
	item_details = {}
	for d in frappe.db.sql("""select name, item_group, brand from `tabItem`""", as_dict=1):
		item_details.setdefault(d.name, d)

	return item_details
