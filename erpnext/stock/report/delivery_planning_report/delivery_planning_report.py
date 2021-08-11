# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import flt, date_diff, getdate

def execute(filters=None):
	group_by = ""

	if filters.group_by == "Transporter":
		group_by =" GROUP BY dpi.Transporter "
	elif filters.group_by == "Customer":
		group_by =" GROUP BY dpi.Customer "
	elif filters.group_by == "Sales Order":
		group_by =" GROUP BY dpi.sales_order "
	elif filters.group_by == "Delivery Date":
		group_by =" GROUP BY dpi.delivery_date "
	else: group_by =""

	validate_filters(filters)
	
	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, group_by, filters)
	return columns, data

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")
	group, based = filters.get("group_by"), filters.get("based_on")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

	# if group == based:
	# 	frappe.throw(_("Group by and Based on cannot be same"))
	


def get_conditions(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " AND dpi.delivery_date between %(from_date)s and %(to_date)s"

	if filters.get("company"):
		conditions += " AND dpi.company = %(company)s"

	if filters.get("transporter"):
		conditions += " AND dpi.transporter = %(transporter)s"

	if filters.get("customer"):
		conditions += " AND dpi.customer = %(customer)s"
		
	return conditions

def get_columns(filters):
	if filters.get("based_on") == "Transporter":
		return [
			_("Sales Order") + ":Link/Sales Order:160",
			_("Customer") +":Link/Customer:120", _("Customer Name") + "::120",
			_("Transporter") + ":Link/Supplier:120", _("Transporter Name") + "::120",
			_("Item Code") + ":Link/Item:120", _("Item Name") + "::120",
			_("Ordered Qty") + ":Float:50", _("Qty To Deliver") + ":Float:50",
			_("Expected Date") + ":Date:90", _("Planned Delivery Date") + ":Date:90",
			_("Delivery Note") + ":Link/Delivery Note:160", _("Delivery Note Date") + ":Date:80",
			_("Delay Days") + ":Int:50", _("Pick List") + ":Link/Pick List:150",
			_("Weight Ordered") + ":Float:100", _("Planned Delivery Weight") + ":Float:100",
			_("Actual Delivery Weight") + ":Float:100", _("Purchase Order") + ":Link/Purchase Order:150",
			_("Supplier") + ":Link/Supplier:120", _("Supplier Name") + "::120",
			_("Item Planning ID") +":Data:100",
			_("Company") + ":Link/Company:120",

	]

def get_data(conditions, group_by, filters):
	query = frappe.db.sql(""" select
							dpi.sales_order,
							dpi.customer,
							dpi.customer_name,
							dpi.transporter,
							dpi.transporter_name,
							dpi.item_code,
							dpi.item_name,
							dpi.ordered_qty,
							dpi.qty_to_deliver,
							dpi.delivery_date as expected_date,
							dpi.planned_date as planned_delivery_date,
							dpi.delivery_note,
							dn.posting_date as delivery_note_date,
							DATEDIFF(dpi.planned_date, dpi.delivery_date) as delay_days,
							dpi.pick_list,
							dpi.weight_to_deliver as weight_ordered,
							dpi.weight_to_deliver as planned_delivery_weight,
							(dni.qty * dpi.weight_per_unit) as actual_delivery_weight,
							dpi.purchase_order as purchase_order,
							dpi.supplier,
							dpi.supplier_name,
							dpi.name as item_planning_id,
							dpi.company,
							dpi.related_delivey_planning as Related_to_Planning
							

							from `tabDelivery Planning Item` dpi
						
							Left join `tabDelivery Note` dn ON dn.name = dpi.delivery_note
							inner join 	`tabDelivery Note Item` dni on dni.parent = dpi.delivery_note 
							and dni.item_code = dpi.item_code
						

							where dpi.docstatus = 1  AND dpi.d_status = "Complete"
						
							
							{conditions}
							{groupby}
							""".format(conditions=conditions, groupby = group_by), filters, as_dict=1)
	return query

