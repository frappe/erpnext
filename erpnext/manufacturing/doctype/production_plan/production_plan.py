# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json, copy
from frappe import msgprint, _
from six import string_types, iteritems

from frappe.model.document import Document
from frappe.utils import cstr, flt, cint, nowdate, add_days, comma_and, now_datetime, ceil
from frappe.utils.csvutils import build_csv_response
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, get_children
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

class ProductionPlan(Document):
	def validate(self):
		self.calculate_total_planned_qty()
		self.set_status()

	def validate_data(self):
		for d in self.get('po_items'):
			if not d.bom_no:
				frappe.throw(_("Please select BOM for Item in Row {0}").format(d.idx))
			else:
				validate_bom_no(d.item_code, d.bom_no)

			if not flt(d.planned_qty):
				frappe.throw(_("Please enter Planned Qty for Item {0} at row {1}").format(d.item_code, d.idx))

	def get_open_sales_orders(self):
		""" Pull sales orders  which are pending to deliver based on criteria selected"""
		open_so = get_sales_orders(self)

		if open_so:
			self.add_so_in_table(open_so)
		else:
			frappe.msgprint(_("Sales orders are not available for production"))

	def add_so_in_table(self, open_so):
		""" Add sales orders in the table"""
		self.set('sales_orders', [])

		for data in open_so:
			self.append('sales_orders', {
				'sales_order': data.name,
				'sales_order_date': data.transaction_date,
				'customer': data.customer,
				'grand_total': data.base_grand_total
			})

	def get_pending_material_requests(self):
		""" Pull Material Requests that are pending based on criteria selected"""
		mr_filter = item_filter = ""
		if self.from_date:
			mr_filter += " and mr.transaction_date >= %(from_date)s"
		if self.to_date:
			mr_filter += " and mr.transaction_date <= %(to_date)s"
		if self.warehouse:
			mr_filter += " and mr_item.warehouse = %(warehouse)s"

		if self.item_code:
			item_filter += " and mr_item.item_code = %(item)s"

		pending_mr = frappe.db.sql("""
			select distinct mr.name, mr.transaction_date
			from `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
			where mr_item.parent = mr.name
				and mr.material_request_type = "Manufacture"
				and mr.docstatus = 1 and mr.company = %(company)s
				and mr_item.qty > ifnull(mr_item.ordered_qty,0) {0} {1}
				and (exists (select name from `tabBOM` bom where bom.item=mr_item.item_code
					and bom.is_active = 1))
			""".format(mr_filter, item_filter), {
				"from_date": self.from_date,
				"to_date": self.to_date,
				"warehouse": self.warehouse,
				"item": self.item_code,
				"company": self.company
			}, as_dict=1)

		self.add_mr_in_table(pending_mr)

	def add_mr_in_table(self, pending_mr):
		""" Add Material Requests in the table"""
		self.set('material_requests', [])

		for data in pending_mr:
			self.append('material_requests', {
				'material_request': data.name,
				'material_request_date': data.transaction_date
			})

	def get_items(self):
		if self.get_items_from == "Sales Order":
			self.get_so_items()
		elif self.get_items_from == "Material Request":
			self.get_mr_items()

	def get_so_mr_list(self, field, table):
		"""Returns a list of Sales Orders or Material Requests from the respective tables"""
		so_mr_list = [d.get(field) for d in self.get(table) if d.get(field)]
		return so_mr_list

	def get_so_items(self):
		# Check for empty table or empty rows
		if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
			frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

		so_list = self.get_so_mr_list("sales_order", "sales_orders")

		item_condition = ""
		if self.item_code:
			item_condition = ' and so_item.item_code = {0}'.format(frappe.db.escape(self.item_code))

		items = frappe.db.sql("""select distinct parent, item_code, warehouse,
			(qty - work_order_qty) * conversion_factor as pending_qty, description, name
			from `tabSales Order Item` so_item
			where parent in (%s) and docstatus = 1 and qty > work_order_qty
			and exists (select name from `tabBOM` bom where bom.item=so_item.item_code
					and bom.is_active = 1) %s""" % \
			(", ".join(["%s"] * len(so_list)), item_condition), tuple(so_list), as_dict=1)

		if self.item_code:
			item_condition = ' and so_item.item_code = {0}'.format(frappe.db.escape(self.item_code))

		packed_items = frappe.db.sql("""select distinct pi.parent, pi.item_code, pi.warehouse as warehouse,
			(((so_item.qty - so_item.work_order_qty) * pi.qty) / so_item.qty)
				as pending_qty, pi.parent_item, pi.description, so_item.name
			from `tabSales Order Item` so_item, `tabPacked Item` pi
			where so_item.parent = pi.parent and so_item.docstatus = 1
			and pi.parent_item = so_item.item_code
			and so_item.parent in (%s) and so_item.qty > so_item.work_order_qty
			and exists (select name from `tabBOM` bom where bom.item=pi.item_code
					and bom.is_active = 1) %s""" % \
			(", ".join(["%s"] * len(so_list)), item_condition), tuple(so_list), as_dict=1)

		self.add_items(items + packed_items)
		self.calculate_total_planned_qty()

	def get_mr_items(self):
		# Check for empty table or empty rows
		if not self.get("material_requests") or not self.get_so_mr_list("material_request", "material_requests"):
			frappe.throw(_("Please fill the Material Requests table"), title=_("Material Requests Required"))

		mr_list = self.get_so_mr_list("material_request", "material_requests")

		item_condition = ""
		if self.item_code:
			item_condition = " and mr_item.item_code ={0}".format(frappe.db.escape(self.item_code))

		items = frappe.db.sql("""select distinct parent, name, item_code, warehouse, description,
			(qty - ordered_qty) * conversion_factor as pending_qty
			from `tabMaterial Request Item` mr_item
			where parent in (%s) and docstatus = 1 and qty > ordered_qty
			and exists (select name from `tabBOM` bom where bom.item=mr_item.item_code
				and bom.is_active = 1) %s""" % \
			(", ".join(["%s"] * len(mr_list)), item_condition), tuple(mr_list), as_dict=1)

		self.add_items(items)
		self.calculate_total_planned_qty()

	def add_items(self, items):
		self.set('po_items', [])
		for data in items:
			item_details = get_item_details(data.item_code)
			pi = self.append('po_items', {
				'include_exploded_items': 1,
				'warehouse': data.warehouse,
				'item_code': data.item_code,
				'description': data.description or item_details.description,
				'stock_uom': item_details and item_details.stock_uom or '',
				'bom_no': item_details and item_details.bom_no or '',
				'planned_qty': data.pending_qty,
				'pending_qty': data.pending_qty,
				'planned_start_date': now_datetime(),
				'product_bundle_item': data.parent_item
			})

			if self.get_items_from == "Sales Order":
				pi.sales_order = data.parent
				pi.sales_order_item = data.name
				pi.description = data.description

			elif self.get_items_from == "Material Request":
				pi.material_request = data.parent
				pi.material_request_item = data.name
				pi.description = data.description

	def calculate_total_planned_qty(self):
		self.total_planned_qty = 0
		for d in self.po_items:
			self.total_planned_qty += flt(d.planned_qty)

	def calculate_total_produced_qty(self):
		self.total_produced_qty = 0
		for d in self.po_items:
			self.total_produced_qty += flt(d.produced_qty)

		self.db_set("total_produced_qty", self.total_produced_qty, update_modified=False)

	def update_produced_qty(self, produced_qty, production_plan_item):
		for data in self.po_items:
			if data.name == production_plan_item:
				data.produced_qty = produced_qty
				data.db_update()

		self.calculate_total_produced_qty()
		self.set_status()
		self.db_set('status', self.status)

	def on_cancel(self):
		self.db_set('status', 'Cancelled')
		self.delete_draft_work_order()

	def delete_draft_work_order(self):
		for d in frappe.get_all('Work Order', fields = ["name"],
			filters = {'docstatus': 0, 'production_plan': ("=", self.name)}):
			frappe.delete_doc('Work Order', d.name)

	def set_status(self, close=None):
		self.status = {
			0: 'Draft',
			1: 'Submitted',
			2: 'Cancelled'
		}.get(self.docstatus)

		if close:
			self.db_set('status', 'Closed')
			return

		if self.total_produced_qty > 0:
			self.status = "In Process"
			if self.total_produced_qty == self.total_planned_qty:
				self.status = "Completed"

		if self.status != 'Completed':
			self.update_ordered_status()
			self.update_requested_status()

		if close is not None:
			self.db_set('status', self.status)

	def update_ordered_status(self):
		update_status = False
		for d in self.po_items:
			if d.planned_qty == d.ordered_qty:
				update_status = True

		if update_status and self.status != 'Completed':
			self.status = 'In Process'

	def update_requested_status(self):
		if not self.mr_items:
			return

		update_status = True
		for d in self.mr_items:
			if d.quantity != d.requested_qty:
				update_status = False

		if update_status:
			self.status = 'Material Requested'

	def get_production_items(self):
		item_dict = {}
		for d in self.po_items:
			item_details= {
				"production_item"		: d.item_code,
				"use_multi_level_bom"   : d.include_exploded_items,
				"sales_order"			: d.sales_order,
				"sales_order_item"		: d.sales_order_item,
				"material_request"		: d.material_request,
				"material_request_item"	: d.material_request_item,
				"bom_no"				: d.bom_no,
				"description"			: d.description,
				"stock_uom"				: d.stock_uom,
				"company"				: self.company,
				"fg_warehouse"			: d.warehouse,
				"production_plan"       : self.name,
				"production_plan_item"  : d.name,
				"product_bundle_item"	: d.product_bundle_item,
				"make_work_order_for_sub_assembly_items": d.get("make_work_order_for_sub_assembly_items", 0)
			}

			item_details.update({
				"project": self.project or frappe.db.get_value("Sales Order", d.sales_order, "project")
			})

			if self.get_items_from == "Material Request":
				item_details.update({
					"qty": d.planned_qty
				})
				item_dict[(d.item_code, d.material_request_item, d.warehouse)] = item_details
			else:
				item_details.update({
					"qty": flt(item_dict.get((d.item_code, d.sales_order, d.warehouse),{})
						.get("qty")) + (flt(d.planned_qty) - flt(d.ordered_qty))
				})
				item_dict[(d.item_code, d.sales_order, d.warehouse)] = item_details

		return item_dict

	def make_work_order(self):
		wo_list = []
		self.validate_data()
		items_data = self.get_production_items()

		for key, item in items_data.items():
			work_order = self.create_work_order(item)
			if work_order:
				wo_list.append(work_order)

			if item.get("make_work_order_for_sub_assembly_items"):
				work_orders = self.make_work_order_for_sub_assembly_items(item)
				wo_list.extend(work_orders)

		frappe.flags.mute_messages = False

		if wo_list:
			wo_list = ["""<a href="#Form/Work Order/%s" target="_blank">%s</a>""" % \
				(p, p) for p in wo_list]
			msgprint(_("{0} created").format(comma_and(wo_list)))
		else :
			msgprint(_("No Work Orders created"))

	def make_work_order_for_sub_assembly_items(self, item):
		work_orders = []
		bom_data = {}

		get_sub_assembly_items(item.get("bom_no"), bom_data, item.get("qty"))

		for key, data in bom_data.items():
			data.update({
				'qty': data.get("stock_qty"),
				'production_plan': self.name,
				'use_multi_level_bom': item.get("use_multi_level_bom"),
				'company': self.company,
				'fg_warehouse': item.get("fg_warehouse"),
				'update_consumed_material_cost_in_project': 0
			})

			work_order = self.create_work_order(data)
			if work_order:
				work_orders.append(work_order)

		return work_orders

	def create_work_order(self, item):
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError, get_default_warehouse
		warehouse = get_default_warehouse()
		wo = frappe.new_doc("Work Order")
		wo.update(item)

		if item.get("warehouse"):
			wo.fg_warehouse = item.get("warehouse")

		wo.set_work_order_operations()

		if not wo.fg_warehouse:
			wo.fg_warehouse = warehouse.get('fg_warehouse')
		try:
			wo.flags.ignore_mandatory = True
			wo.insert()
			return wo.name
		except OverProductionError:
			pass

	def make_material_request(self):
		'''Create Material Requests grouped by Sales Order and Material Request Type'''
		material_request_list = []
		material_request_map = {}

		for item in self.mr_items:
			item_doc = frappe.get_cached_doc('Item', item.item_code)

			material_request_type = item.material_request_type or item_doc.default_material_request_type

			# key for Sales Order:Material Request Type:Customer
			key = '{}:{}:{}'.format(item.sales_order, material_request_type, item_doc.customer or '')
			schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))

			if not key in material_request_map:
				# make a new MR for the combination
				material_request_map[key] = frappe.new_doc("Material Request")
				material_request = material_request_map[key]
				material_request.update({
					"transaction_date": nowdate(),
					"status": "Draft",
					"company": self.company,
					'material_request_type': material_request_type,
					'customer': item_doc.customer or ''
				})
				material_request_list.append(material_request)
			else:
				material_request = material_request_map[key]

			# add item
			material_request.append("items", {
				"item_code": item.item_code,
				"from_warehouse": item.from_warehouse,
				"qty": item.quantity,
				"schedule_date": schedule_date,
				"warehouse": item.warehouse,
				"sales_order": item.sales_order,
				'production_plan': self.name,
				'material_request_plan_item': item.name,
				"project": frappe.db.get_value("Sales Order", item.sales_order, "project") \
					if item.sales_order else None
			})

		for material_request in material_request_list:
			# submit
			material_request.flags.ignore_permissions = 1
			material_request.run_method("set_missing_values")

			if self.get('submit_material_request'):
				material_request.submit()
			else:
				material_request.save()

		frappe.flags.mute_messages = False

		if material_request_list:
			material_request_list = ["""<a href="#Form/Material Request/{0}">{1}</a>""".format(m.name, m.name) \
				for m in material_request_list]
			msgprint(_("{0} created").format(comma_and(material_request_list)))
		else :
			msgprint(_("No material request created"))

@frappe.whitelist()
def download_raw_materials(doc):
	if isinstance(doc, string_types):
		doc = frappe._dict(json.loads(doc))

	item_list = [['Item Code', 'Description', 'Stock UOM', 'Warehouse', 'Required Qty as per BOM',
		'Projected Qty', 'Actual Qty', 'Ordered Qty', 'Reserved Qty for Production',
		'Safety Stock', 'Required Qty']]

	for d in get_items_for_material_requests(doc):
		item_list.append([d.get('item_code'), d.get('description'), d.get('stock_uom'), d.get('warehouse'),
			d.get('required_bom_qty'), d.get('projected_qty'), d.get('actual_qty'), d.get('ordered_qty'),
			d.get('reserved_qty_for_production'), d.get('safety_stock'), d.get('quantity')])

		if not doc.get('for_warehouse'):
			row = {'item_code': d.get('item_code')}
			for bin_dict in get_bin_details(row, doc.company, all_warehouse=True):
				if d.get("warehouse") == bin_dict.get('warehouse'):
					continue

				item_list.append(['', '', '', bin_dict.get('warehouse'), '',
					bin_dict.get('projected_qty', 0), bin_dict.get('actual_qty', 0),
					bin_dict.get('ordered_qty', 0), bin_dict.get('reserved_qty_for_production', 0)])

	build_csv_response(item_list, doc.name)

def get_exploded_items(item_details, company, bom_no, include_non_stock_items, planned_qty=1):
	for d in frappe.db.sql("""select bei.item_code, item.default_bom as bom,
			ifnull(sum(bei.stock_qty/ifnull(bom.quantity, 1)), 0)*%s as qty, item.item_name,
			bei.description, bei.stock_uom, item.min_order_qty, bei.source_warehouse,
			item.default_material_request_type, item.min_order_qty, item_default.default_warehouse,
			item.purchase_uom, item_uom.conversion_factor
		from
			`tabBOM Explosion Item` bei
			JOIN `tabBOM` bom ON bom.name = bei.parent
			JOIN `tabItem` item ON item.name = bei.item_code
			LEFT JOIN `tabItem Default` item_default
				ON item_default.parent = item.name and item_default.company=%s
			LEFT JOIN `tabUOM Conversion Detail` item_uom
				ON item.name = item_uom.parent and item_uom.uom = item.purchase_uom
		where
			bei.docstatus < 2
			and bom.name=%s and item.is_stock_item in (1, {0})
		group by bei.item_code, bei.stock_uom""".format(0 if include_non_stock_items else 1),
		(planned_qty, company, bom_no), as_dict=1):
			item_details.setdefault(d.get('item_code'), d)
	return item_details

def get_subitems(doc, data, item_details, bom_no, company, include_non_stock_items,
	include_subcontracted_items, parent_qty, planned_qty=1):
	items = frappe.db.sql("""
		SELECT
			bom_item.item_code, default_material_request_type, item.item_name,
			ifnull(%(parent_qty)s * sum(bom_item.stock_qty/ifnull(bom.quantity, 1)) * %(planned_qty)s, 0) as qty,
			item.is_sub_contracted_item as is_sub_contracted, bom_item.source_warehouse,
			item.default_bom as default_bom, bom_item.description as description,
			bom_item.stock_uom as stock_uom, item.min_order_qty as min_order_qty, item.safety_stock as safety_stock,
			item_default.default_warehouse, item.purchase_uom, item_uom.conversion_factor
		FROM
			`tabBOM Item` bom_item
			JOIN `tabBOM` bom ON bom.name = bom_item.parent
			JOIN tabItem item ON bom_item.item_code = item.name
			LEFT JOIN `tabItem Default` item_default
				ON item.name = item_default.parent and item_default.company = %(company)s
			LEFT JOIN `tabUOM Conversion Detail` item_uom
				ON item.name = item_uom.parent and item_uom.uom = item.purchase_uom
		where
			bom.name = %(bom)s
			and bom_item.docstatus < 2
			and item.is_stock_item in (1, {0})
		group by bom_item.item_code""".format(0 if include_non_stock_items else 1),{
			'bom': bom_no,
			'parent_qty': parent_qty,
			'planned_qty': planned_qty,
			'company': company
		}, as_dict=1)

	for d in items:
		if not data.get('include_exploded_items') or not d.default_bom:
			if d.item_code in item_details:
				item_details[d.item_code].qty = item_details[d.item_code].qty + d.qty
			else:
				item_details[d.item_code] = d

		if data.get('include_exploded_items') and d.default_bom:
			if ((d.default_material_request_type in ["Manufacture", "Purchase"] and
				not d.is_sub_contracted) or (d.is_sub_contracted and include_subcontracted_items)):
				if d.qty > 0:
					get_subitems(doc, data, item_details, d.default_bom, company,
						include_non_stock_items, include_subcontracted_items, d.qty)
	return item_details

def get_material_request_items(row, sales_order, company,
	ignore_existing_ordered_qty, include_safety_stock, warehouse, bin_dict):
	total_qty = row['qty']

	required_qty = 0
	if ignore_existing_ordered_qty or bin_dict.get("projected_qty", 0) < 0:
		required_qty = total_qty
	elif total_qty > bin_dict.get("projected_qty", 0):
		required_qty = total_qty - bin_dict.get("projected_qty", 0)
	if required_qty > 0 and required_qty < row['min_order_qty']:
		required_qty = row['min_order_qty']
	item_group_defaults = get_item_group_defaults(row.item_code, company)

	if not row['purchase_uom']:
		row['purchase_uom'] = row['stock_uom']

	if row['purchase_uom'] != row['stock_uom']:
		if not row['conversion_factor']:
			frappe.throw(_("UOM Conversion factor ({0} -> {1}) not found for item: {2}")
				.format(row['purchase_uom'], row['stock_uom'], row.item_code))
		required_qty = required_qty / row['conversion_factor']

	if frappe.db.get_value("UOM", row['purchase_uom'], "must_be_whole_number"):
		required_qty = ceil(required_qty)

	if include_safety_stock:
		required_qty += flt(row['safety_stock'])

	if required_qty > 0:
		return {
			'item_code': row.item_code,
			'item_name': row.item_name,
			'quantity': required_qty,
			'required_bom_qty': total_qty,
			'description': row.description,
			'stock_uom': row.get("stock_uom"),
			'warehouse': warehouse or row.get('source_warehouse') \
				or row.get('default_warehouse') or item_group_defaults.get("default_warehouse"),
			'safety_stock': row.safety_stock,
			'actual_qty': bin_dict.get("actual_qty", 0),
			'projected_qty': bin_dict.get("projected_qty", 0),
			'ordered_qty': bin_dict.get("ordered_qty", 0),
			'reserved_qty_for_production': bin_dict.get("reserved_qty_for_production", 0),
			'min_order_qty': row['min_order_qty'],
			'material_request_type': row.get("default_material_request_type"),
			'sales_order': sales_order,
			'description': row.get("description"),
			'uom': row.get("purchase_uom") or row.get("stock_uom")
		}

def get_sales_orders(self):
	so_filter = item_filter = ""
	if self.from_date:
		so_filter += " and so.transaction_date >= %(from_date)s"
	if self.to_date:
		so_filter += " and so.transaction_date <= %(to_date)s"
	if self.customer:
		so_filter += " and so.customer = %(customer)s"
	if self.project:
		so_filter += " and so.project = %(project)s"
	if self.sales_order_status:
		so_filter += "and so.status = %(sales_order_status)s"

	if self.item_code:
		item_filter += " and so_item.item_code = %(item)s"

	open_so = frappe.db.sql("""
		select distinct so.name, so.transaction_date, so.customer, so.base_grand_total
		from `tabSales Order` so, `tabSales Order Item` so_item
		where so_item.parent = so.name
			and so.docstatus = 1 and so.status not in ("Stopped", "Closed")
			and so.company = %(company)s
			and so_item.qty > so_item.work_order_qty {0} {1}
			and (exists (select name from `tabBOM` bom where bom.item=so_item.item_code
					and bom.is_active = 1)
				or exists (select name from `tabPacked Item` pi
					where pi.parent = so.name and pi.parent_item = so_item.item_code
						and exists (select name from `tabBOM` bom where bom.item=pi.item_code
							and bom.is_active = 1)))
		""".format(so_filter, item_filter), {
			"from_date": self.from_date,
			"to_date": self.to_date,
			"customer": self.customer,
			"project": self.project,
			"item": self.item_code,
			"company": self.company,
			"sales_order_status": self.sales_order_status
		}, as_dict=1)
	return open_so

@frappe.whitelist()
def get_bin_details(row, company, for_warehouse=None, all_warehouse=False):
	if isinstance(row, string_types):
		row = frappe._dict(json.loads(row))

	company = frappe.db.escape(company)
	conditions, warehouse = "", ""

	conditions = " and warehouse in (select name from `tabWarehouse` where company = {0})".format(company)
	if not all_warehouse:
		warehouse = for_warehouse or row.get('source_warehouse') or row.get('default_warehouse')

	if warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		conditions = """ and warehouse in (select name from `tabWarehouse`
			where lft >= {0} and rgt <= {1} and name=`tabBin`.warehouse and company = {2})
		""".format(lft, rgt, company)

	return frappe.db.sql(""" select ifnull(sum(projected_qty),0) as projected_qty,
		ifnull(sum(actual_qty),0) as actual_qty, ifnull(sum(ordered_qty),0) as ordered_qty,
		ifnull(sum(reserved_qty_for_production),0) as reserved_qty_for_production, warehouse from `tabBin`
		where item_code = %(item_code)s {conditions}
		group by item_code, warehouse
	""".format(conditions=conditions), { "item_code": row['item_code'] }, as_dict=1)

@frappe.whitelist()
def get_items_for_material_requests(doc, warehouses=None):
	if isinstance(doc, string_types):
		doc = frappe._dict(json.loads(doc))

	warehouse_list = []
	if warehouses:
		if isinstance(warehouses, string_types):
			warehouses = json.loads(warehouses)

		for row in warehouses:
			child_warehouses = frappe.db.get_descendants('Warehouse', row.get("warehouse"))
			if child_warehouses:
				warehouse_list.extend(child_warehouses)
			else:
				warehouse_list.append(row.get("warehouse"))

	if warehouse_list:
		warehouses = list(set(warehouse_list))

		if doc.get("for_warehouse") and doc.get("for_warehouse") in warehouses:
			warehouses.remove(doc.get("for_warehouse"))

		warehouse_list = None

	doc['mr_items'] = []

	po_items = doc.get('po_items') if doc.get('po_items') else doc.get('items')
	# Check for empty table or empty rows
	if not po_items or not [row.get('item_code') for row in po_items if row.get('item_code')]:
		frappe.throw(_("Items to Manufacture are required to pull the Raw Materials associated with it."),
			title=_("Items Required"))

	company = doc.get('company')
	ignore_existing_ordered_qty = doc.get('ignore_existing_ordered_qty')
	include_safety_stock = doc.get('include_safety_stock')

	so_item_details = frappe._dict()
	for data in po_items:
		planned_qty = data.get('required_qty') or data.get('planned_qty')
		ignore_existing_ordered_qty = data.get('ignore_existing_ordered_qty') or ignore_existing_ordered_qty
		warehouse = doc.get('for_warehouse')

		item_details = {}
		if data.get("bom") or data.get("bom_no"):
			if data.get('required_qty'):
				bom_no = data.get('bom')
				include_non_stock_items = 1
				include_subcontracted_items = 1 if data.get('include_exploded_items') else 0
			else:
				bom_no = data.get('bom_no')
				include_subcontracted_items = doc.get('include_subcontracted_items')
				include_non_stock_items = doc.get('include_non_stock_items')

			if not planned_qty:
				frappe.throw(_("For row {0}: Enter Planned Qty").format(data.get('idx')))

			if bom_no:
				if data.get('include_exploded_items') and include_subcontracted_items:
					# fetch exploded items from BOM
					item_details = get_exploded_items(item_details,
						company, bom_no, include_non_stock_items, planned_qty=planned_qty)
				else:
					item_details = get_subitems(doc, data, item_details, bom_no, company,
						include_non_stock_items, include_subcontracted_items, 1, planned_qty=planned_qty)
		elif data.get('item_code'):
			item_master = frappe.get_doc('Item', data['item_code']).as_dict()
			purchase_uom = item_master.purchase_uom or item_master.stock_uom
			conversion_factor = 0
			for d in item_master.get("uoms"):
				if d.uom == purchase_uom:
					conversion_factor = d.conversion_factor

			item_details[item_master.name] = frappe._dict(
				{
					'item_name' : item_master.item_name,
					'default_bom' : doc.bom,
					'purchase_uom' : purchase_uom,
					'default_warehouse': item_master.default_warehouse,
					'min_order_qty' : item_master.min_order_qty,
					'default_material_request_type' : item_master.default_material_request_type,
					'qty': planned_qty or 1,
					'is_sub_contracted' : item_master.is_subcontracted_item,
					'item_code' : item_master.name,
					'description' : item_master.description,
					'stock_uom' : item_master.stock_uom,
					'conversion_factor' : conversion_factor,
					'safety_stock': item_master.safety_stock
				}
			)

		sales_order = doc.get("sales_order")

		for item_code, details in iteritems(item_details):
			so_item_details.setdefault(sales_order, frappe._dict())
			if item_code in so_item_details.get(sales_order, {}):
				so_item_details[sales_order][item_code]['qty'] = so_item_details[sales_order][item_code].get("qty", 0) + flt(details.qty)
			else:
				so_item_details[sales_order][item_code] = details

	mr_items = []
	for sales_order, item_code in iteritems(so_item_details):
		item_dict = so_item_details[sales_order]
		for details in item_dict.values():
			bin_dict = get_bin_details(details, doc.company, warehouse)
			bin_dict = bin_dict[0] if bin_dict else {}

			if details.qty > 0:
				items = get_material_request_items(details, sales_order, company,
					ignore_existing_ordered_qty, include_safety_stock, warehouse, bin_dict)
				if items:
					mr_items.append(items)

	if not ignore_existing_ordered_qty and warehouses:
		new_mr_items = []
		for item in mr_items:
			get_materials_from_other_locations(item, warehouses, new_mr_items, company)

		mr_items = new_mr_items

	if not mr_items:
		to_enable = frappe.bold(_("Ignore Existing Projected Quantity"))
		warehouse = frappe.bold(doc.get('for_warehouse'))
		message = _("As there are sufficient raw materials, Material Request is not required for Warehouse {0}.").format(warehouse) + "<br><br>"
		message += _(" If you still want to proceed, please enable {0}.").format(to_enable)

		frappe.msgprint(message, title=_("Note"))

	return mr_items

def get_materials_from_other_locations(item, warehouses, new_mr_items, company):
	from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations
	locations = get_available_item_locations(item.get("item_code"),
		warehouses, item.get("quantity"), company, ignore_validation=True)

	if not locations:
		new_mr_items.append(item)
		return

	required_qty = item.get("quantity")
	for d in locations:
		if required_qty <=0: return

		new_dict = copy.deepcopy(item)
		quantity = required_qty if d.get("qty") > required_qty else d.get("qty")

		if required_qty > 0:
			new_dict.update({
				"quantity": quantity,
				"material_request_type": "Material Transfer",
				"from_warehouse": d.get("warehouse")
			})

			required_qty -= quantity
			new_mr_items.append(new_dict)

	if required_qty:
		item["quantity"] = required_qty
		new_mr_items.append(item)

@frappe.whitelist()
def get_item_data(item_code):
	item_details = get_item_details(item_code)

	return {
		"bom_no": item_details.get("bom_no"),
		"stock_uom": item_details.get("stock_uom")
#		"description": item_details.get("description")
	}

def get_sub_assembly_items(bom_no, bom_data, to_produce_qty):
	data = get_children('BOM', parent = bom_no)
	for d in data:
		if d.expandable:
			key = (d.name, d.value)
			if key not in bom_data:
				bom_data.setdefault(key, {
					'stock_qty': 0,
					'description': d.description,
					'production_item': d.item_code,
					'item_name': d.item_name,
					'stock_uom': d.stock_uom,
					'uom': d.stock_uom,
					'bom_no': d.value
				})

			bom_item = bom_data.get(key)
			bom_item["stock_qty"] += (d.stock_qty / d.parent_bom_qty) * flt(to_produce_qty)

			get_sub_assembly_items(bom_item.get("bom_no"), bom_data, bom_item["stock_qty"])
