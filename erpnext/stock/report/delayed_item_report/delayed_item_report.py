# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import date_diff


def execute(filters=None, consolidated = False):
	data, columns = DelayedItemReport(filters).run()

	return data, columns

class DelayedItemReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		return self.get_columns(), self.get_data() or []

	def get_data(self, consolidated=False):
		conditions = ""

		doctype = self.filters.get("based_on")
		child_doc= "%s Item" % doctype

		if doctype == "Sales Invoice":
			conditions = " and `tabSales Invoice`.update_stock = 1 and `tabSales Invoice`.is_pos = 0"

		if self.filters.get("item_group"):
			conditions += " and `tab%s`.item_group = %s" % (child_doc,
				frappe.db.escape(self.filters.get("item_group")))

		for field in ["customer", "customer_group", "company"]:
			if self.filters.get(field):
				conditions += " and `tab%s`.%s = %s" % (doctype,
					field, frappe.db.escape(self.filters.get(field)))

		sales_order_field = "against_sales_order"
		if doctype == "Sales Invoice":
			sales_order_field = "sales_order"

		if self.filters.get("sales_order"):
			conditions = " and `tab%s`.%s = '%s'" %(child_doc, sales_order_field, self.filters.get("sales_order"))

		self.transactions = frappe.db.sql(""" SELECT `tab{child_doc}`.item_code, `tab{child_doc}`.item_name,
				`tab{child_doc}`.item_group, `tab{child_doc}`.qty, `tab{child_doc}`.rate, `tab{child_doc}`.amount,
				`tab{child_doc}`.so_detail, `tab{child_doc}`.{so_field} as sales_order,
				`tab{doctype}`.shipping_address_name, `tab{doctype}`.po_no, `tab{doctype}`.customer,
				`tab{doctype}`.posting_date, `tab{doctype}`.name, `tab{doctype}`.grand_total
			FROM `tab{child_doc}`, `tab{doctype}`
			WHERE
				`tab{child_doc}`.parent = `tab{doctype}`.name and `tab{doctype}`.docstatus = 1 and
				`tab{doctype}`.posting_date between %(from_date)s and %(to_date)s and
				`tab{child_doc}`.{so_field} is not null and `tab{child_doc}`.{so_field} != '' {cond}
		""".format(cond=conditions, doctype=doctype, child_doc=child_doc, so_field=sales_order_field), {
			'from_date': self.filters.get('from_date'),
			'to_date': self.filters.get('to_date')
		}, as_dict=1)

		if self.transactions:
			self.filter_transactions_data(consolidated)

			return self.transactions

	def filter_transactions_data(self, consolidated=False):
		sales_orders = [d.sales_order for d in self.transactions]
		doctype = "Sales Order"
		filters = {'name': ('in', sales_orders)}

		if not consolidated:
			sales_order_items = [d.so_detail for d in self.transactions]
			doctype = "Sales Order Item"
			filters = {'parent': ('in', sales_orders), 'name': ('in', sales_order_items)}

		so_data = {}
		for d in frappe.get_all(doctype, filters = filters,
			fields = ["delivery_date", "parent", "name"]):
			key = d.name if consolidated else (d.parent, d.name)
			if key not in so_data:
				so_data.setdefault(key, d.delivery_date)

		for row in self.transactions:
			key = row.sales_order if consolidated else (row.sales_order, row.so_detail)
			row.update({
				'delivery_date': so_data.get(key),
				'delayed_days': date_diff(row.posting_date, so_data.get(key))
			})

		return self.transactions

	def get_columns(self):
		based_on = self.filters.get("based_on")

		return [{
			"label": _(based_on),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": based_on,
			"width": 100
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200
		},
		{
			"label": _("Shipping Address"),
			"fieldname": "shipping_address_name",
			"fieldtype": "Link",
			"options": "Address",
			"width": 120
		},
		{
			"label": _("Expected Delivery Date"),
			"fieldname": "delivery_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Actual Delivery Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Delayed Days"),
			"fieldname": "delayed_days",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 100
		},
		{
			"label": _("Customer PO"),
			"fieldname": "po_no",
			"fieldtype": "Data",
			"width": 100
		}]
