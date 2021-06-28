# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	conditions = ""
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

	if filters.company:
		conditions +="AND pl.company = %s" % frappe.db.escape(filters.company)

	if filters.transporter:
		conditions += "AND dpi.transporter = %s" % frappe.db.escape(filters.transporter)

	if filters.from_date:
		conditions += "AND dpi.delivery_date >= '%s'" % filters.from_date

	if filters.to_date:
		conditions += "AND dpi.delivery_date <= '%s'" % filters.to_date

	if filters.customer:
		conditions += "AND dpi.customer = %s" % frappe.db.escape(filters.customer)
	columns = get_column()
	data = get_data(conditions, group_by)
	return columns, data



def get_column():
	return [
		_("Sales Order") + ":Link/Sales Order:160",
		_("Customer") +":Link/Customer:120", _("Customer Name") + "::120",
		_("Transporter") + ":Link/Supplier:120", _("Transporter Name") + "::120",
		_("Item Code") + ":Link/Item:120", _("Item Name") + "::120",
		_("Ordered Qty") + ":Float:50", _("Qty To Deliver") + ":Float:50",
		_("Expected Date") + ":Date:100", _("Planned Delivery Date") + ":Date:100",
		_("Delivery Note") + ":Link/Delivery Note:160", _("Delivery Note Date") + ":Date:100",
		_("Delay Days") + ":Int:50", _("Pick List") + ":Link/Pick List:180",
		_("Weight Ordered") + ":Float:100", _("Planned Delivery Weight") + ":Float:100",
		_("Actual Delivery Weight") + ":Float:100", _("Purchase Order") + ":Link/Purchase Order:180",
		_("Company") + ":Link/Company:120",

	]

def get_data(conditions, group_by):
	query = frappe.db.sql(""" select
							dpi.sales_order,
							dpi.customer,
							c.customer_name,
							dpi.transporter,
							s.supplier_name as transporter_name,
							dpi.item_code,
							dpi.item_name,
							dpi.ordered_qty,
							dpi.qty_to_deliver,
							dpi.delivery_date as expected_date,
							dpi.delivery_date as planned_delivery_date,
							dn.name as delivery_note,
							dn.posting_date as delivery_note_date,
							DATEDIFF(dpi.delivery_date, dn.posting_date) as delay_days,
							pl.name as pick_list,
							dpi.weight_to_deliver as weight_ordered,
							dpi.weight_to_deliver as palnned_delivery_weight,
							pl.total_weight as actual_delivery_weight,
							# po.name as purchase_order,
							pl.company

							from `tabDelivery Planning Item` dpi

							Left join `tabDelivery Note` dn
							ON dn.related_delivery_planning = dpi.related_delivey_planning

							Left join `tabPick List` pl
							ON pl.customer = dn.customer

							Left join `tabPurchase Order` po
							ON dpi.related_delivey_planning = pl.related_delivery_planning

							Left join `tabCustomer` c ON dpi.customer = c.name
							Left join `tabSupplier` s ON dpi.transporter = s.name


							where pl.docstatus = 1 AND dn.docstatus = 1 AND dpi.approved = "Yes"
							AND dn.related_delivery_planning = dpi.related_delivey_planning
							AND pl.customer = dn.customer
							AND dpi.related_delivey_planning = pl.related_delivery_planning
							AND dpi.customer = c.name
							AND dpi.transporter = s.name
							{conditions}
							{group_by}""".format(conditions=conditions, group_by=group_by), as_dict=1)
	return query

