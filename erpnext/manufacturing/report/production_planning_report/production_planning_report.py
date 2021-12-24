# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

# and bom_no is not null and bom_no !=''

mapper = {
	"Sales Order": {
		"fields": """ item_code as production_item, item_name as production_item_name, stock_uom,
			stock_qty as qty_to_manufacture, `tabSales Order Item`.parent as name, bom_no, warehouse,
			`tabSales Order Item`.delivery_date, `tabSales Order`.base_grand_total """,
		"filters": """`tabSales Order Item`.docstatus = 1 and stock_qty > produced_qty
			and `tabSales Order`.per_delivered < 100.0"""
	},
	"Material Request": {
		"fields": """ item_code as production_item, item_name as production_item_name, stock_uom,
			stock_qty as qty_to_manufacture, `tabMaterial Request Item`.parent as name, bom_no, warehouse,
			`tabMaterial Request Item`.schedule_date """,
		"filters": """`tabMaterial Request`.docstatus = 1 and `tabMaterial Request`.per_ordered < 100
			and `tabMaterial Request`.material_request_type = 'Manufacture' """
	},
	"Work Order": {
		"fields": """ production_item, item_name as production_item_name, planned_start_date,
			stock_uom, qty as qty_to_manufacture, name, bom_no, fg_warehouse as warehouse """,
		"filters": "docstatus = 1 and status not in ('Completed', 'Stopped')"
	},
}

order_mapper = {
	"Sales Order": {
		"Delivery Date": "`tabSales Order Item`.delivery_date asc",
		"Total Amount": "`tabSales Order`.base_grand_total desc"
	},
	"Material Request": {
		"Required Date": "`tabMaterial Request Item`.schedule_date asc"
	},
	"Work Order": {
		"Planned Start Date": "planned_start_date asc"
	}
}

def execute(filters=None):
	return ProductionPlanReport(filters).execute_report()

class ProductionPlanReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.raw_materials_dict = {}
		self.data = []

	def execute_report(self):
		self.get_open_orders()
		self.get_raw_materials()
		self.get_item_details()
		self.get_bin_details()
		self.get_purchase_details()
		self.prepare_data()
		self.get_columns()

		return self.columns, self.data

	def get_open_orders(self):
		doctype = ("`tabWork Order`" if self.filters.based_on == "Work Order"
			else "`tab{doc}`, `tab{doc} Item`".format(doc=self.filters.based_on))

		filters = mapper.get(self.filters.based_on)["filters"]
		filters = self.prepare_other_conditions(filters, self.filters.based_on)
		order_by = " ORDER BY %s" % (order_mapper[self.filters.based_on][self.filters.order_by])

		self.orders = frappe.db.sql(""" SELECT {fields} from {doctype}
			WHERE {filters} {order_by}""".format(
				doctype = doctype,
				filters = filters,
				order_by = order_by,
				fields = mapper.get(self.filters.based_on)["fields"]
			), tuple(self.filters.docnames), as_dict=1)

	def prepare_other_conditions(self, filters, doctype):
		if self.filters.docnames:
			field = "name" if doctype == "Work Order" else "`tab{} Item`.parent".format(doctype)
			filters += " and %s in (%s)" % (field, ','.join(['%s'] * len(self.filters.docnames)))

		if doctype != "Work Order":
			filters += " and `tab{doc}`.name = `tab{doc} Item`.parent".format(doc=doctype)

		if self.filters.company:
			filters += " and `tab%s`.company = %s" %(doctype, frappe.db.escape(self.filters.company))

		return filters

	def get_raw_materials(self):
		if not self.orders: return
		self.warehouses = [d.warehouse for d in self.orders]
		self.item_codes = [d.production_item for d in self.orders]

		if self.filters.based_on == "Work Order":
			work_orders = [d.name for d in self.orders]

			raw_materials = frappe.get_all("Work Order Item",
				fields=["parent", "item_code", "item_name as raw_material_name",
					"source_warehouse as warehouse", "required_qty"],
				filters = {"docstatus": 1, "parent": ("in", work_orders), "source_warehouse": ("!=", "")}) or []
			self.warehouses.extend([d.source_warehouse for d in raw_materials])

		else:
			bom_nos = []

			for d in self.orders:
				bom_no = d.bom_no or frappe.get_cached_value("Item", d.production_item, "default_bom")

				if not d.bom_no:
					d.bom_no = bom_no

				bom_nos.append(bom_no)

			bom_doctype = ("BOM Explosion Item"
				if self.filters.include_subassembly_raw_materials else "BOM Item")

			qty_field = ("qty_consumed_per_unit"
				if self.filters.include_subassembly_raw_materials else "(bom_item.qty / bom.quantity)")

			raw_materials = frappe.db.sql(""" SELECT bom_item.parent, bom_item.item_code,
					bom_item.item_name as raw_material_name, {0} as required_qty_per_unit
				FROM
					`tabBOM` as bom, `tab{1}` as bom_item
				WHERE
					bom_item.parent in ({2}) and bom_item.parent = bom.name and bom.docstatus = 1
			""".format(qty_field, bom_doctype, ','.join(["%s"] * len(bom_nos))), tuple(bom_nos), as_dict=1)

		if not raw_materials: return

		self.item_codes.extend([d.item_code for d in raw_materials])

		for d in raw_materials:
			if d.parent not in self.raw_materials_dict:
				self.raw_materials_dict.setdefault(d.parent, [])

			rows = self.raw_materials_dict[d.parent]
			rows.append(d)

	def get_item_details(self):
		if not (self.orders and self.item_codes): return

		self.item_details = {}
		for d in frappe.get_all("Item Default", fields = ["parent", "default_warehouse"],
			filters = {"company": self.filters.company, "parent": ("in", self.item_codes)}):
			self.item_details[d.parent] = d

	def get_bin_details(self):
		if not (self.orders and self.raw_materials_dict): return

		self.bin_details = {}
		self.mrp_warehouses = []
		if self.filters.raw_material_warehouse:
			self.mrp_warehouses.extend(get_child_warehouses(self.filters.raw_material_warehouse))
			self.warehouses.extend(self.mrp_warehouses)

		for d in frappe.get_all("Bin",
			fields=["warehouse", "item_code", "actual_qty", "ordered_qty", "projected_qty"],
			filters = {"item_code": ("in", self.item_codes), "warehouse": ("in", self.warehouses)}):
			key = (d.item_code, d.warehouse)
			if key not in self.bin_details:
				self.bin_details.setdefault(key, d)

	def get_purchase_details(self):
		if not (self.orders and self.raw_materials_dict): return

		self.purchase_details = {}

		for d in frappe.get_all("Purchase Order Item",
			fields=["item_code", "min(schedule_date) as arrival_date", "qty as arrival_qty", "warehouse"],
			filters = {"item_code": ("in", self.item_codes), "warehouse": ("in", self.warehouses)},
			group_by = "item_code, warehouse"):
			key = (d.item_code, d.warehouse)
			if key not in self.purchase_details:
				self.purchase_details.setdefault(key, d)

	def prepare_data(self):
		if not self.orders: return

		for d in self.orders:
			key = d.name if self.filters.based_on == "Work Order" else d.bom_no

			if not self.raw_materials_dict.get(key): continue

			bin_data = self.bin_details.get((d.production_item, d.warehouse)) or {}
			d.update({
				"for_warehouse": d.warehouse,
				"available_qty": 0
			})

			if bin_data and bin_data.get("actual_qty") > 0 and d.qty_to_manufacture:
				d.available_qty = (bin_data.get("actual_qty")
					if (d.qty_to_manufacture > bin_data.get("actual_qty")) else d.qty_to_manufacture)

				bin_data["actual_qty"] -= d.available_qty

			self.update_raw_materials(d, key)

	def update_raw_materials(self, data, key):
		self.index = 0
		self.raw_materials_dict.get(key)

		warehouses = self.mrp_warehouses or []
		for d in self.raw_materials_dict.get(key):
			if self.filters.based_on != "Work Order":
				d.required_qty = d.required_qty_per_unit * data.qty_to_manufacture

			if not warehouses:
				warehouses = [data.warehouse]

			if self.filters.based_on == "Work Order" and d.warehouse:
				warehouses = [d.warehouse]
			else:
				item_details = self.item_details.get(d.item_code)
				if item_details:
					warehouses = [item_details["default_warehouse"]]

			if self.filters.raw_material_warehouse:
				warehouses = get_child_warehouses(self.filters.raw_material_warehouse)

			d.remaining_qty = d.required_qty
			self.pick_materials_from_warehouses(d, data, warehouses)

			if (d.remaining_qty and self.filters.raw_material_warehouse
				and d.remaining_qty != d.required_qty):
				row = self.get_args()
				d.warehouse = self.filters.raw_material_warehouse
				d.required_qty = d.remaining_qty
				d.allotted_qty = 0
				row.update(d)
				self.data.append(row)

	def pick_materials_from_warehouses(self, args, order_data, warehouses):
		for index, warehouse in enumerate(warehouses):
			if not args.remaining_qty: return

			row = self.get_args()

			key = (args.item_code, warehouse)
			bin_data = self.bin_details.get(key)

			if bin_data:
				row.update(bin_data)

			args.allotted_qty = 0
			if bin_data and bin_data.get("actual_qty") > 0:
				args.allotted_qty = (bin_data.get("actual_qty")
					if (args.required_qty > bin_data.get("actual_qty")) else args.required_qty)

				args.remaining_qty -= args.allotted_qty
				bin_data["actual_qty"] -= args.allotted_qty

			if ((self.mrp_warehouses and (args.allotted_qty or index == len(warehouses) - 1))
				or not self.mrp_warehouses):
				if not self.index:
					row.update(order_data)
					self.index += 1

				args.warehouse = warehouse
				row.update(args)
				if self.purchase_details.get(key):
					row.update(self.purchase_details.get(key))

				self.data.append(row)

	def get_args(self):
		return frappe._dict({
			"work_order": "",
			"sales_order": "",
			"production_item": "",
			"production_item_name": "",
			"qty_to_manufacture": "",
			"produced_qty": ""
		})

	def get_columns(self):
		based_on = self.filters.based_on

		self.columns = [{
			"label": _("ID"),
			"options": based_on,
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 100
		}, {
			"label": _("Item Code"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		}, {
			"label": _("Item Name"),
			"fieldname": "production_item_name",
			"fieldtype": "Data",
			"width": 130
		}, {
			"label": _("Warehouse"),
			"options": "Warehouse",
			"fieldname": "for_warehouse",
			"fieldtype": "Link",
			"width": 100
		}, {
			"label": _("Order Qty"),
			"fieldname": "qty_to_manufacture",
			"fieldtype": "Float",
			"width": 80
		}, {
			"label": _("Available"),
			"fieldname": "available_qty",
			"fieldtype": "Float",
			"width": 80
		}]

		fieldname, fieldtype = "delivery_date", "Date"
		if self.filters.based_on == "Sales Order" and self.filters.order_by == "Total Amount":
			fieldname, fieldtype = "base_grand_total", "Currency"
		elif self.filters.based_on == "Material Request":
			fieldname = "schedule_date"
		elif self.filters.based_on == "Work Order":
			fieldname = "planned_start_date"

		self.columns.append({
			"label": _(self.filters.order_by),
			"fieldname": fieldname,
			"fieldtype": fieldtype,
			"width": 100
		})

		self.columns.extend([{
			"label": _("Raw Material Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		}, {
			"label": _("Raw Material Name"),
			"fieldname": "raw_material_name",
			"fieldtype": "Data",
			"width": 130
		}, {
			"label": _("Warehouse"),
			"options": "Warehouse",
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"width": 110
		}, {
			"label": _("Required Qty"),
			"fieldname": "required_qty",
			"fieldtype": "Float",
			"width": 100
		}, {
			"label": _("Allotted Qty"),
			"fieldname": "allotted_qty",
			"fieldtype": "Float",
			"width": 100
		}, {
			"label": _("Expected Arrival Date"),
			"fieldname": "arrival_date",
			"fieldtype": "Date",
			"width": 160
		}, {
			"label": _("Arrival Quantity"),
			"fieldname": "arrival_qty",
			"fieldtype": "Float",
			"width": 140
		}])
