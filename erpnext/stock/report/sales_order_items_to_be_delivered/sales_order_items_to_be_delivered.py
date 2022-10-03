# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cstr, getdate
from six import iteritems, string_types


class OrderItemFulfilmentTracker:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or dict())
		self.filters.company = filters.company or frappe.db.get_single_value('Global Defaults', 'default_company')

	def run(self, doctype):
		self.filters.doctype = doctype

		if self.filters.doctype == "Sales Order":
			self.filters.party_type = "Customer"
		elif self.filters.doctype == "Purchase Order":
			self.filters.party_type = "Supplier"

		self.get_columns()
		self.get_invoices()
		return self.columns, self.data

	def get_invoices(self):
		self.get_fields()
		self.get_conditions()

		orders = frappe.db.sql("""
			SELECT
				o.company, o.name, o.status, o.transaction_date, o.{party_type} as party, o.project,
				o.{schedule_date} as schedule_date, o.currency, i.item_code, i.{qty_field} as qty,
				i.{completed_qty} as completed_qty, i.warehouse, i.item_name, i.brand, i.rate, i.amount
			FROM `tab{doctype}` o
			INNER JOIN `tab{doctype} Item` i ON i.parent = o.name
			INNER JOIN `tabItem` im on im.name = i.item_code
			WHERE
				o.docstatus = 1 AND o.status != 'Closed' AND im.is_stock_item = 1
				{conditions}
			ORDER BY o.transaction_date
		""".format(
				party_type=self.fields.party,
				schedule_date=self.fields.schedule_date,
				qty_field=self.fields.qty,
				completed_qty=self.fields.completed_qty,
				doctype=self.filters.doctype,
				conditions = self.conditions
			), self.filters, as_dict=1)

		stock_qty_date = []

		item_warehouse_list = list(set([(d.item_code, d.warehouse) for d in orders]))
		if item_warehouse_list:
			stock_qty_data = frappe.db.sql("""
				select item_code, warehouse, sum(actual_qty) as actual_qty
				from `tabBin`
				where (item_code, warehouse) in %s
				group by item_code, warehouse
			""", [item_warehouse_list], as_dict=1,debug=1)

		stock_qty_map = {}
		for d in stock_qty_data:
			key = (d.item_code, d.warehouse)
			stock_qty_map[key] = d.actual_qty

		for d in orders:
			d["remaining_qty"] = d["qty"] - d["completed_qty"]
			d["delay_days"] = max((getdate() - d["schedule_date"]).days, 0)
			d["actual_qty"] = flt(stock_qty_map.get((d.item_code, d.warehouse)))

		self.data = orders

	def get_conditions(self):
		conditions = list()
		if self.filters.company:
			conditions.append("o.company = %(company)s")

		if self.filters.transaction_type:
			conditions.append("o.transaction_type = %(transaction_type)s")

		if self.filters.customer:
			conditions.append("o.customer = %(customer)s")

		if self.filters.customer_group:
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""
				o.customer_group IN (
					SELECT name
					FROM `tabCustomer Group`
					WHERE lft>={0} AND rgt<={1} AND docstatus<2)
				""".format(lft, rgt))

		if self.filters.item_code:
			if frappe.db.get_value("Item", self.filters.item_code, 'has_variants'):
				conditions.append("im.variant_of = %(item_code)s")
			else:
				conditions.append("i.item_code = %(item_code)s")

		if self.filters.item_group:
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""
				im.item_group IN (
					SELECT name
					FROM `tabItem Group`
					WHERE lft>=%s AND rgt<=%s AND docstatus<2)""" % (lft, rgt))

		if self.filters.brand:
			conditions.append("im.brand = %(brand)s")

		if self.filters.item_source:
			conditions.append("im.item_source = %(item_source)s")

		if self.filters.project:
			if isinstance(self.filters.project, string_types):
				self.filters.project = [d.strip() for d in cstr(self.filters.project).split(',')]
			conditions.append("o.project in %(project)s")

		if self.filters.doctype == "Sales Order":
			conditions.append("i.delivered_qty < qty")
		elif self.filters.doctype == "Purchase Order":
			conditions.append("i.received_qty < qty")

		self.conditions = "AND {}".format(" AND ".join(conditions)) if conditions else ""

	def get_fields(self):
		fields = frappe._dict({})
		if self.filters.doctype == "Sales Order":
			fields.completed_qty = "delivered_qty"
			fields.schedule_date = "delivery_date"
			fields.party = "customer"
		elif self.filters.doctype == "Purchase Order":
			fields.completed_qty = "received_qty"
			fields.schedule_date = "schedule_date"
			fields.party = "supplier"

		fields.qty = self.get_qty_fieldname()
		self.fields = fields

	def get_qty_fieldname(self):
		filter_to_field = {
			"Stock Qty": "stock_qty",
			"Contents Qty": "alt_uom_qty",
			"Transaction Qty": "qty"
		}
		return filter_to_field.get(self.filters.qty_field) or "stock_qty"

	def get_columns(self):
		columns = [
			{
				"label": _(self.filters.doctype),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": self.filters.doctype,
				"width": 140
			},
			{
				"label": _(self.filters.party_type),
				"fieldname": "party",
				"fieldtype": "Link",
				"options": self.filters.party_type,
				"width": 80
			},
			{
				"label": _("Order Date"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Item"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Link",
				"options": "Item",
				"width": 150
			},
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Received" if self.filters.doctype == "Sales Order" else "Delivered"),
				"fieldname": "completed_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Remaining"),
				"fieldname": "remaining_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("In Stock"),
				"fieldname": "actual_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Rate"),
				"fieldname": "rate",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Scheduled Date"),
				"fieldname": "schedule_date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Delay Days"),
				"fieldname": "delay_days",
				"fieldtype": "Int",
				"width": 90
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100
			},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 90
			},
			{
				"label": _("Brand"),
				"fieldname": "brand",
				"fieldtype": "Link",
				"options": "Brand",
				"width": 60
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 90
			},
			{
				"label": _("Status"),
				"fieldname": "status",
				"fieldtype": "Data",
				"width": 120
			},
		]

		self.columns = columns
		return self.columns


def execute(filters=None):
	return OrderItemFulfilmentTracker(filters).run("Sales Order")
