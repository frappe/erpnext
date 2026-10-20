# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnext.stock.report.delayed_item_report.delayed_item_report import DelayedItemReport


def execute(filters=None):
	columns, data = [], []

	columns, data = DelayedOrderReport(filters).run()

	return columns, data


class DelayedOrderReport(DelayedItemReport):
	def run(self):
		return self.get_columns(), self.get_data(consolidated=True) or []

	def get_data(self, consolidated=False):
		data = super().get_data(consolidated) or []

		last_deliveries = {}
		for d in data:
			if flt(d.qty) <= 0:
				continue

			last = last_deliveries.get(d.sales_order)
			if not last or getdate(d.posting_date) > getdate(last.posting_date):
				last_deliveries[d.sales_order] = d

		order_totals = dict(
			frappe.get_all(
				"Sales Order",
				filters={"name": ("in", list(last_deliveries))},
				fields=["name", "grand_total"],
				as_list=True,
			)
		)
		for sales_order, row in last_deliveries.items():
			row.grand_total = order_totals.get(sales_order)

		return list(last_deliveries.values())

	def get_columns(self):
		based_on = self.filters.get("based_on")

		return [
			{
				"label": _(based_on),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": based_on,
				"width": 100,
			},
			{
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Link",
				"options": "Customer",
				"width": 200,
			},
			{
				"label": _("Shipping Address"),
				"fieldname": "shipping_address_name",
				"fieldtype": "Link",
				"options": "Address",
				"width": 140,
			},
			{
				"label": _("Expected Delivery Date"),
				"fieldname": "delivery_date",
				"fieldtype": "Date",
				"width": 100,
			},
			{
				"label": _("Actual Delivery Date"),
				"fieldname": "posting_date",
				"fieldtype": "Date",
				"width": 100,
			},
			{"label": _("Amount"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 100},
			{"label": _("Delayed Days"), "fieldname": "delayed_days", "fieldtype": "Int", "width": 100},
			{
				"label": _("Sales Order"),
				"fieldname": "sales_order",
				"fieldtype": "Link",
				"options": "Sales Order",
				"width": 150,
			},
			{"label": _("Customer PO"), "fieldname": "po_no", "fieldtype": "Data", "width": 110},
		]
