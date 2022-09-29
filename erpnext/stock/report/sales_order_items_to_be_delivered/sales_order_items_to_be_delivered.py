# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cstr
from six import iteritems, string_types

class OrderItemFullfilmentTracker:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or dict())
		self.filters.company = filters.company or frappe.db.get_single_value('Global Defaults', 'default_company')

	def run(self):
		self.get_columns()
		self.get_conditions()
		self.get_invoices()
		return self.columns, self.data

	def get_invoices(self):
		filter_qty = ""
		if self.filters.qty_field:
			filter_to_field = {
				"Stock Qty": "stock_qty",
				"Contents Qty": "alt_uom_qty",
				"Transaction Qty": "qty"
			}
			filter_qty = filter_to_field.get(self.filters.qty_field, "stock_qty")

		orders = frappe.db.sql("""
			SELECT
				o.name, o.status, o.transaction_date as date, o.delivery_date, o.customer, o.customer_name, o.project,
				o.company, i.item_code, i.{0} as qty, i.delivered_qty, i.warehouse, i.item_name, i.description, i.brand
			FROM `tabSales Order` o
			LEFT JOIN `tabSales Order Item` i
				ON i.parent = o.name
			LEFT JOIN `tabItem` im
				ON i.item_code = im.name
			WHERE
				o.docstatus = 1 AND o.status != 'Closed' AND i.delivered_qty < i.qty {1}
			ORDER BY o.name
		""".format(filter_qty, self.conditions), self.filters, as_dict=1)

		for record in orders:
			record["remaining_qty"] = record['qty'] - record['delivered_qty']

		self.data = orders

	def get_conditions(self):
		conditions = list()
		if self.filters.company:
			conditions.append("o.company = %(company)s")

		if self.filters.transaction_type:
			conditions.append("o.transaction_type = %(transaction_type)s")

		if self.filters.customer:
			conditions.append("o.customer = %(customer)s")

		if self.filters.item_source:
			conditions.append("i.item_source = %(item_source)s")

		if self.filters.brand:
			conditions.append("i.brand = %(brand)s")

		if self.filters.customer_group:
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""
				o.customer_group IN (
					SELECT name
					FROM `tabCustomer Group`
					WHERE lft>={} AND rgt<={} AND docstatus<2)
				""".format(lft, rgt))

		if self.filters.item_code:
			if frappe.db.get_value("Item", self.filters.item_code, 'has_variants'):
				conditions.append("im.variant_of=%(item_code)s")
			else:
				conditions.append("i.item_code=%(item_code)s")

		if self.filters.item_group:
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""
				i.item_group IN (
					SELECT name
					FROM `tabItem Group`
					WHERE lft>=%s AND rgt<=%s AND docstatus<2)""" % (lft, rgt))

		if self.filters.project:
			if isinstance(self.filters.project, string_types):
				self.filters.project = [d.strip() for d in cstr(self.filters.project).split(',')]
			conditions.append("o.project in %(project)s")

		self.conditions = "AND {}".format(" AND ".join(conditions)) if conditions else ""

	def get_columns(self):
		self.columns = [
			{
				"label": _("Sales Order Number"),
				"fieldname": "name",
				"fieldtype": "Data",
				"width": 140
			},
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Link",
				"options": "Item",
				"width": 90
			},
			{
				"label": _("Status"),
				"fieldname": "status",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Creation Date"),
				"fieldname": "date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Delivery Date"),
				"fieldname": "delivery_date",
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Customer"),
				"fieldname": "customer",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "data",
				"width": 90
			},
			{
				"label": _("Description"),
				"fieldname": "description",
				"fieldtype": "data",
				"width": 150
			},
			{
				"label": _("Brand"),
				"fieldname": "brand",
				"fieldtype": "data",
				"width": 100
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "data",
				"width": 150
			},
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Int",
				"width": 110
			},
			{
				"label": _("Delivered Qty"),
				"fieldname": "delivered_qty",
				"fieldtype": "Int",
				"width": 110
			},
			{
				"label": _("Remaining Qty"),
				"fieldname": "remaining_qty",
				"fieldtype": "Int",
				"width": 110
			}
		]


def execute(filters=None):
	return OrderItemFullfilmentTracker(filters).run()
