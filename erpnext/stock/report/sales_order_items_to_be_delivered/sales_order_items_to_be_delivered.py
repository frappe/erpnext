# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, cstr, getdate
from six import iteritems, string_types


def execute(filters=None):
	return OrderItemFulfilmentTracker(filters).run("Sales Order")

class OrderItemFulfilmentTracker:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or dict())

	def run(self, doctype):
		self.filters.doctype = doctype
		self.filters.party_type = "Customer" if doctype == "Sales Order" else "Supplier"
		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		self.show_party_name = False
		if self.filters.party_type == "Customer":
			self.show_party_name = frappe.defaults.get_global_default('cust_master_name') == "Naming Series"
		if self.filters.party_type == "Supplier":
			self.show_party_name = frappe.defaults.get_global_default('supp_master_name') == "Naming Series"

		self.get_columns()
		self.get_data()
		self.prepare_data()

		return self.columns, self.data

	def get_data(self):
		fieldnames = self.get_fieldnames()
		conditions = self.get_conditions()

		party_join = ""
		if self.filters.party_type == "Customer":
			party_join = "inner join `tabCustomer` cus on cus.name = o.customer"
		elif self.filters.party_type == "Supplier":
			party_join = "inner join `tabSupplier` sup on sup.name = o.supplier"

		orders = frappe.db.sql("""
			SELECT
				o.name, o.company, o.status, o.transaction_date, o.{schedule_date_field} as schedule_date,
				o.{party_field} as party, o.{party_name_field} as party_name, o.project, o.currency,
				i.item_code, i.item_name, i.warehouse,
				i.{qty_field} as qty, i.{completed_qty_field} as completed_qty,
				i.rate, i.amount,
				i.uom, i.stock_uom, i.alt_uom,
				i.brand, i.item_group
			FROM `tab{doctype}` o
			INNER JOIN `tab{doctype} Item` i ON i.parent = o.name
			INNER JOIN `tabItem` im on im.name = i.item_code
			{party_join}
			WHERE
				o.docstatus = 1 AND o.status != 'Closed' AND i.{completed_qty_field} < i.qty AND im.is_stock_item = 1
				{conditions}
			ORDER BY o.transaction_date, o.creation
		""".format(
				party_field=fieldnames.party,
				party_name_field=fieldnames.party_name,
				schedule_date_field=fieldnames.schedule_date,
				qty_field=fieldnames.qty,
				completed_qty_field=fieldnames.completed_qty,
				doctype=self.filters.doctype,
				party_join=party_join,
				conditions=conditions
			), self.filters, as_dict=1)

		self.data = orders

	def get_fieldnames(self):
		fields = frappe._dict({})
		if self.filters.doctype == "Sales Order":
			fields.completed_qty = "delivered_qty"
			fields.schedule_date = "delivery_date"

			fields.party = "customer"
			fields.party_name = "customer_name"
		elif self.filters.doctype == "Purchase Order":
			fields.completed_qty = "received_qty"
			fields.schedule_date = "schedule_date"

			fields.party = "supplier"
			fields.party_name = "supplier_name"

		fields.qty = self.get_qty_fieldname()
		return fields

	def get_qty_fieldname(self):
		filter_to_field = {
			"Stock Qty": "stock_qty",
			"Contents Qty": "alt_uom_qty",
			"Transaction Qty": "qty"
		}
		return filter_to_field.get(self.filters.qty_field) or "stock_qty"

	def get_conditions(self):
		conditions = []

		if self.filters.company:
			conditions.append("o.company = %(company)s")

		if self.filters.name:
			conditions.append("o.name = %(name)s")

		if self.filters.transaction_type:
			conditions.append("o.transaction_type = %(transaction_type)s")

		if self.filters.customer:
			conditions.append("o.customer = %(customer)s")

		if self.filters.supplier:
			conditions.append("o.supplier = %(supplier)s")

		if self.filters.customer_group:
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""cus.customer_group IN (SELECT name FROM `tabCustomer Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.supplier_group:
			lft, rgt = frappe.db.get_value("Supplier Group", self.filters.supplier_group, ["lft", "rgt"])
			conditions.append("""sup.supplier_group IN (SELECT name FROM `tabSupplier Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.item_code:
			if frappe.db.get_value("Item", self.filters.item_code, 'has_variants'):
				conditions.append("im.variant_of = %(item_code)s")
			else:
				conditions.append("i.item_code = %(item_code)s")

		if self.filters.item_group:
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""im.item_group IN (SELECT name FROM `tabItem Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.brand:
			conditions.append("im.brand = %(brand)s")

		if self.filters.item_source:
			conditions.append("im.item_source = %(item_source)s")

		if self.filters.get("project"):
			if isinstance(self.filters.project, string_types):
				self.filters.project = cstr(self.filters.get("project")).strip()
				self.filters.project = [d.strip() for d in self.filters.project.split(',') if d]

			if frappe.get_meta(self.filters.doctype + " Item").has_field("project") and frappe.get_meta(self.filters.doctype).has_field("project"):
				conditions.append("IF(i.project IS NULL or i.project = '', o.project, i.project) in %(project)s")
			elif frappe.get_meta(self.filters.doctype + " Item").has_field("project"):
				conditions.append("i.project in %(project)s")
			elif frappe.get_meta(self.filters.doctype).has_field("project"):
				conditions.append("o.project in %(project)s")

		if self.filters.get("warehouse"):
			lft, rgt = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"])
			conditions.append("""i.warehouse in (select name from `tabWarehouse`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		return "AND {}".format(" AND ".join(conditions)) if conditions else ""

	def prepare_data(self):
		stock_qty_map = self.get_stock_qty_map()

		for d in self.data:
			# Set UOM based on qty field
			if self.filters.qty_field == "Transaction Qty":
				d.uom = d.uom
			elif self.filters.qty_field == "Contents Qty":
				d.uom = d.alt_uom or d.stock_uom
			else:
				d.uom = d.stock_uom

			d['rate'] = d['amount'] / d['qty'] if d['qty'] else d['rate']

			d["remaining_qty"] = d["qty"] - d["completed_qty"]
			d["actual_qty"] = flt(stock_qty_map.get((d.item_code, d.warehouse)))

			d["delay_days"] = max((getdate() - d["schedule_date"]).days, 0)

			d["disable_item_formatter"] = cint(self.show_item_name)
			d["disable_party_name_formatter"] = cint(self.show_party_name)

	def get_stock_qty_map(self):
		stock_qty_data = []

		item_warehouse_list = list(set([(d.item_code, d.warehouse) for d in self.data]))
		if item_warehouse_list:
			stock_qty_data = frappe.db.sql("""
				select item_code, warehouse, sum(actual_qty) as actual_qty
				from `tabBin`
				where (item_code, warehouse) in %s
				group by item_code, warehouse
			""", [item_warehouse_list], as_dict=1)

		stock_qty_map = {}
		for d in stock_qty_data:
			key = (d.item_code, d.warehouse)
			stock_qty_map[key] = d.actual_qty

		return stock_qty_map


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
				"width": 80 if self.show_party_name else 150
			},
			{
				"label": _(self.filters.party_type) + " Name",
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Order Date"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100 if self.show_item_name else 150
			},
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 90
			},
			{
				"label": _("UOM"),
				"fieldtype": "Link",
				"options": "UOM",
				"fieldname": "uom",
				"width": 50
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
				"width": 85
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100
			},
			{
				"label": _("Status"),
				"fieldname": "status",
				"fieldtype": "Data",
				"width": 120
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
		]

		if not self.show_item_name:
			columns = [c for c in columns if c['fieldname'] != 'item_name']
		
		if not self.show_party_name:
			columns = [c for c in columns if c['fieldname'] != 'party_name']

		self.columns = columns
		return self.columns
