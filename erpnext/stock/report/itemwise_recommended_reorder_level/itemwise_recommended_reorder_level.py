# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import getdate, flt

def execute(filters=None):
	if not filters: filters = {}
	float_preceision = frappe.db.get_default("float_preceision")

	condition = get_condition(filters)

	avg_daily_outgoing = 0
	diff = ((getdate(filters.get("to_date")) - getdate(filters.get("from_date"))).days)+1
	if diff <= 0:
		frappe.throw(_("'From Date' must be after 'To Date'"))

	columns = get_columns()
	items = get_item_info(filters)
	consumed_item_map = get_consumed_items(condition)
	delivered_item_map = get_delivered_items(condition)

	data = []
	for item in items:
		total_outgoing = consumed_item_map.get(item.name, 0) + delivered_item_map.get(item.name,0)
		avg_daily_outgoing = flt(total_outgoing / diff, float_preceision)
		reorder_level = (avg_daily_outgoing * flt(item.lead_time_days)) + flt(item.safety_stock)

		data.append([item.name, item.item_name, item.item_group, item.brand, item.description,
			item.safety_stock, item.lead_time_days, consumed_item_map.get(item.name, 0),
			delivered_item_map.get(item.name,0), total_outgoing, avg_daily_outgoing, reorder_level])

	return columns , data

def get_columns():
	return[
			_("Item") + ":Link/Item:120", _("Item Name") + ":Data:120", _("Item Group") + ":Link/Item Group:100",
			_("Brand") + ":Link/Brand:100", _("Description") + "::160",
			_("Safety Stock") + ":Float:160", _("Lead Time Days") + ":Float:120", _("Consumed") + ":Float:120",
			_("Delivered") + ":Float:120", _("Total Outgoing") + ":Float:120", _("Avg Daily Outgoing") + ":Float:160",
			_("Reorder Level") + ":Float:120"
	]

def get_item_info(filters):
	from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition
	conditions = [get_item_group_condition(filters.get("item_group"))]
	if filters.get("brand"):
		conditions.append("item.brand=%(brand)s")

	return frappe.db.sql("""select name, item_name, description, brand, item_group,
		safety_stock, lead_time_days from `tabItem` item where {}"""
		.format(" and ".join(conditions)), filters, as_dict=1)


def get_consumed_items(condition):
	cn_items = frappe.db.sql("""select se_item.item_code,
			sum(se_item.transfer_qty) as 'consume_qty'
		from `tabStock Entry` se, `tabStock Entry Detail` se_item
		where se.name = se_item.parent and se.docstatus = 1
		and (ifnull(se_item.t_warehouse, '') = '' or se.purpose = 'Subcontract') %s
		group by se_item.item_code""" % (condition), as_dict=1)

	cn_items_map = {}
	for item in cn_items:
		cn_items_map.setdefault(item.item_code, item.consume_qty)

	return cn_items_map

def get_delivered_items(condition):
	dn_items = frappe.db.sql("""select dn_item.item_code, sum(dn_item.stock_qty) as dn_qty
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where dn.name = dn_item.parent and dn.docstatus = 1 %s
		group by dn_item.item_code""" % (condition), as_dict=1)

	si_items = frappe.db.sql("""select si_item.item_code, sum(si_item.stock_qty) as si_qty
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name = si_item.parent and si.docstatus = 1 and
		si.update_stock = 1 %s
		group by si_item.item_code""" % (condition), as_dict=1)

	dn_item_map = {}
	for item in dn_items:
		dn_item_map.setdefault(item.item_code, item.dn_qty)

	for item in si_items:
		dn_item_map.setdefault(item.item_code, item.si_qty)

	return dn_item_map

def get_condition(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and posting_date between '%s' and '%s'" % (filters["from_date"],filters["to_date"])
	else:
		frappe.throw(_("From and To dates required"))
	return conditions
