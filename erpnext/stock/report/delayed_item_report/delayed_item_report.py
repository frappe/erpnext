# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import date_diff


def execute(filters=None, consolidated=False):
	data, columns = DelayedItemReport(filters).run()

	return data, columns


class DelayedItemReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

	def run(self):
		return self.get_columns(), self.get_data() or []

	def get_data(self, consolidated=False):
		doctype = self.filters.get("based_on")
		sales_order_field = "sales_order" if doctype == "Sales Invoice" else "against_sales_order"

		parent = frappe.qb.DocType(doctype)
		child = frappe.qb.DocType(f"{doctype} Item")

		query = (
			frappe.qb.from_(child)
			.from_(parent)
			.select(
				child.item_code,
				child.item_name,
				child.item_group,
				child.qty,
				child.rate,
				child.amount,
				child.so_detail,
				child[sales_order_field].as_("sales_order"),
				parent.shipping_address_name,
				parent.po_no,
				parent.customer,
				parent.posting_date,
				parent.name,
				parent.grand_total,
			)
			.where(
				(child.parent == parent.name)
				& (parent.docstatus == 1)
				& (parent.posting_date.between(self.filters.get("from_date"), self.filters.get("to_date")))
				& (child[sales_order_field].notnull())
				& (child[sales_order_field] != "")
			)
		)

		if doctype == "Sales Invoice":
			query = query.where((parent.update_stock == 1) & (parent.is_pos == 0))

		if self.filters.get("item_group"):
			query = query.where(child.item_group == self.filters.get("item_group"))

		if self.filters.get("sales_order"):
			query = query.where(child[sales_order_field] == self.filters.get("sales_order"))

		for field in ("customer", "customer_group", "company"):
			if self.filters.get(field):
				query = query.where(parent[field] == self.filters.get(field))

		self.transactions = query.run(as_dict=True)

		if self.transactions:
			self.filter_transactions_data(consolidated)

			return self.transactions

	def filter_transactions_data(self, consolidated=False):
		sales_orders = [d.sales_order for d in self.transactions]
		doctype = "Sales Order"
		filters = {"name": ("in", sales_orders)}

		if not consolidated:
			sales_order_items = [d.so_detail for d in self.transactions]
			doctype = "Sales Order Item"
			filters = {"parent": ("in", sales_orders), "name": ("in", sales_order_items)}

		so_data = {}
		for d in frappe.get_all(doctype, filters=filters, fields=["delivery_date", "parent", "name"]):
			key = d.name if consolidated else (d.parent, d.name)
			if key not in so_data:
				so_data.setdefault(key, d.delivery_date)

		for row in self.transactions:
			key = row.sales_order if consolidated else (row.sales_order, row.so_detail)
			row.update(
				{
					"delivery_date": so_data.get(key),
					"delayed_days": date_diff(row.posting_date, so_data.get(key)),
				}
			)

		return self.transactions

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
				"width": 120,
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
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
			{"label": _("Quantity"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
			{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
			{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
			{"label": _("Delayed Days"), "fieldname": "delayed_days", "fieldtype": "Int", "width": 100},
			{
				"label": _("Sales Order"),
				"fieldname": "sales_order",
				"fieldtype": "Link",
				"options": "Sales Order",
				"width": 100,
			},
			{"label": _("Customer PO"), "fieldname": "po_no", "fieldtype": "Data", "width": 100},
		]
