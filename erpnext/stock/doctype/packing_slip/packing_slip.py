# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.mapper import map_child_doc
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.get_item_details import get_conversion_factor, get_hide_item_code, get_weight_per_unit,\
	get_default_expense_account, get_default_cost_center, get_item_default_values, get_force_default_warehouse,\
	get_global_default_warehouse
from erpnext.accounts.party import validate_party_frozen_disabled
import json


force_item_fields = ["stock_uom", "has_batch_no", "has_serial_no", "force_default_warehouse"]


class PackingSlip(StockController):
	item_table_fields = ["items", "packaging_items"]

	def get_feed(self):
		return _("Packed {0}").format(self.get("package_type"))

	def validate(self):
		self.validate_posting_time()
		super(PackingSlip, self).validate()
		self.validate_contents_mandatory()
		self.validate_items()
		self.validate_children_packing_slips()
		self.validate_sales_orders()
		self.validate_customer()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_with_previous_doc()
		self.calculate_totals()
		self.validate_weights()
		self.set_title()
		self.set_delivery_status(validate_delivery=False)
		self.set_status()

	def on_submit(self):
		self.update_previous_doc_status()
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.update_previous_doc_status()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

	def set_title(self):
		self.title = self.package_type
		if self.get("customer"):
			self.title += " for {0}".format(self.customer_name or self.customer)

	def set_missing_values(self, for_validate=False):
		self.set_missing_item_details(for_validate)

	def set_missing_item_details(self, for_validate=False):
		parent_args = self.as_dict()
		for field in self.item_table_fields:
			for item in self.get(field):
				if item.item_code:
					args = parent_args.copy()
					args.update(item.as_dict())
					args.doctype = self.doctype
					args.name = self.name
					args.child_doctype = item.doctype

					item_details = get_item_details(args)
					for f in item_details:
						if f in force_item_fields or not item.get(f):
							item.set(f, item_details.get(f))

	def validate_children_packing_slips(self):
		pass

	def validate_contents_mandatory(self):
		if not self.get("items") and not self.get("packing_slips"):
			frappe.throw(_("Please enter Packed Items or Packed Packaged"))

	def validate_items(self):
		from erpnext.stock.doctype.item.item import validate_end_of_life

		item_codes = []
		for field in self.item_table_fields:
			for d in self.get(field):
				if d.item_code:
					item_codes.append(d.item_code)

		stock_items = self.get_stock_items(item_codes)
		for field in self.item_table_fields:
			for d in self.get(field):
				if d.item_code:
					item = frappe.get_cached_value("Item", d.item_code, ['has_variants', 'end_of_life', 'disabled'], as_dict=1)
					validate_end_of_life(d.item_code, end_of_life=item.end_of_life, disabled=item.disabled)

					if cint(item.has_variants):
						frappe.throw(_("Row #{0}: {1} is a template Item, please select one of its variants")
							.format(d.idx, frappe.bold(d.item_code)))

					if d.item_code not in stock_items:
						frappe.throw(_("Row #{0}: {1} is not a stock Item")
							.format(d.idx, frappe.bold(d.item_code)))

					if not flt(d.qty):
						frappe.throw(_("Row #{0}: Item {1}, Quantity cannot be 0").format(d.idx, frappe.bold(d.item_code)))

					if flt(d.qty) < 0:
						frappe.throw(_("Row #{0}: Item {1}, quantity must be positive number")
							.format(d.idx, frappe.bold(d.item_code)))

	def validate_with_previous_doc(self):
		super(PackingSlip, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="]]
			},
			"Sales Order Item": {
				"ref_dn_field": "sales_order_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
		})

	def validate_weights(self):
		weight_fields = ["net_weight", "tare_weight", "gross_weight"]

		for table_field in self.item_table_fields:
			for d in self.get(table_field):
				for weight_field in weight_fields:
					if d.meta.has_field(weight_field) and flt(d.get(weight_field)) < 0:
						frappe.throw(_("Row #{0}: {1} cannot be negative").format(d.idx, d.meta.get_label(weight_field)))

		if flt(self.total_tare_weight) < 0:
			frappe.throw(_("Total Tare Weight cannot be negative"))

		if flt(self.total_gross_weight) < 0:
			frappe.throw(_("Total Gross Weight cannot be negative"))

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_warehouse_company

		warehouses = []
		for field in self.item_table_fields:
			warehouses += [d.source_warehouse for d in self.get(field) if d.get("source_warehouse")]

		warehouses = list(set(warehouses))
		for w in warehouses:
			validate_warehouse_company(w, self.company)

	def determine_warehouse_from_sales_order(self):
		sales_order_row_names = [d.sales_order_item for d in self.get("items") if d.get("sales_order_item")]
		if sales_order_row_names:
			warehouses = frappe.db.sql_list("""
				select distinct warehouse
				from `tabSales Order Item`
				where name in %s
			""", [sales_order_row_names])

			if warehouses and len(warehouses) == 1 and warehouses[0]:
				self.warehouse = warehouses[0]

	def validate_sales_orders(self):
		sales_orders = list(set([d.sales_order for d in self.get("items") if d.get("sales_order")]))
		sales_order_map = {}
		for sales_order in sales_orders:
			details = frappe.db.get_value("Sales Order", sales_order,
				["name", "docstatus", "status", "customer", "customer_name"], as_dict=1)
			sales_order_map[sales_order] = details

		customer_details = frappe._dict({})
		for d in self.get("items"):
			if not d.get("sales_order"):
				continue

			order_details = sales_order_map[d.sales_order]
			if order_details.docstatus == 0:
				frappe.throw(_("Row #{0}: {1} is Draft. Please submit it first.").format(
					d.idx, frappe.get_desk_link("Sales Order", order_details.name)))
			if order_details.docstatus == 2:
				frappe.throw(_("Row #{0}: {1} is cancelled").format(
					d.idx, frappe.get_desk_link("Sales Order", order_details.name)))
			if order_details.status in ("Closed", "On Hold"):
				frappe.throw(_("Row #{0}: {1} status is {2}").format(
					d.idx, frappe.get_desk_link("Sales Order", order_details.name), frappe.bold(order_details.status)))

			if customer_details and customer_details.customer != order_details.customer:
				frappe.throw(_("Row #{0}: {1} Customer {2} does not match with Row #{3} {4} Customer {5}").format(
					d.idx,
					frappe.get_desk_link("Sales Order", order_details.name),
					order_details.customer_name or order_details.customer,
					customer_details.row.idx,
					frappe.get_desk_link("Sales Order", customer_details.sales_order),
					customer_details.customer_name or customer_details.customer,
				))

			customer_details.customer = order_details.customer
			customer_details.customer_name = order_details.customer_name
			customer_details.row = d
			customer_details.sales_order = d.sales_order

		if customer_details and customer_details.customer:
			self.customer = customer_details.customer
			self.customer_name = customer_details.customer_name

	def validate_customer(self):
		if self.get("customer"):
			validate_party_frozen_disabled("Customer", self.customer)
			self.customer_name = frappe.get_cached_value("Customer", self.customer, "customer_name")
		else:
			self.customer_name = None

	def calculate_totals(self):
		self.total_net_weight = 0
		self.total_tare_weight = 0

		for field in self.item_table_fields:
			for item in self.get(field):
				self.round_floats_in(item,
					excluding=['net_weight_per_unit', 'tare_weight_per_unit', 'gross_weight_per_unit'])

				item.stock_qty = item.qty * item.conversion_factor

				if item.meta.has_field("net_weight_per_unit"):
					item.net_weight = flt(item.net_weight_per_unit * item.stock_qty, item.precision("net_weight"))
				if item.meta.has_field("tare_weight_per_unit"):
					item.tare_weight = flt(item.tare_weight_per_unit * item.stock_qty, item.precision("tare_weight"))
				if item.meta.has_field("gross_weight"):
					item.gross_weight = flt(item.net_weight + item.tare_weight, item.precision("gross_weight"))
					if item.stock_qty and item.meta.has_field("gross_weight_per_unit"):
						item.gross_weight_per_unit = item.gross_weight / item.stock_qty

				self.total_net_weight += flt(item.get("net_weight"))
				self.total_tare_weight += flt(item.get("tare_weight"))

		for item in self.get("packing_slips"):
			self.total_net_weight += item.net_weight
			self.total_tare_weight += item.tare_weight

		self.round_floats_in(self, ['total_net_weight', 'total_tare_weight'])
		self.total_gross_weight = flt(self.total_net_weight + self.total_tare_weight, self.precision("total_gross_weight"))

	def update_previous_doc_status(self):
		sales_orders = set()
		sales_order_row_names = set()

		for d in self.items:
			if d.sales_order:
				sales_orders.add(d.sales_order)
			if d.sales_order_item:
				sales_order_row_names.add(d.sales_order_item)

		for name in sales_orders:
			doc = frappe.get_doc("Sales Order", name)
			doc.set_packing_status(update=True)
			doc.validate_packed_qty(from_doctype=self.doctype, row_names=sales_order_row_names)
			doc.notify_update()

	def update_stock_ledger(self, allow_negative_stock=False):
		sl_entries = []

		# SLE for items contents source warehouse
		for d in self.get('items'):
			sl_entries.append(self.get_sl_entries(d, {
				"warehouse": d.source_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"incoming_rate": 0
			}))

		# SLE for item contents target warehouse
		for d in self.get('items'):
			sle = self.get_sl_entries(d, {
				"warehouse": self.warehouse,
				"actual_qty": flt(d.stock_qty),
				"packing_slip": self.name,
				# "incoming_rate": flt(d.valuation_rate)
			})

			# SLE Dependency
			if self.docstatus == 1:
				sle.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": self.name,
					"dependent_voucher_detail_no": d.name,
					"dependency_type": "Amount",
				}]

			sl_entries.append(sle)

		# SLE for packaging material
		for d in self.get('packaging_items'):
			sl_entries.append(self.get_sl_entries(d, {
				"warehouse": d.source_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"incoming_rate": 0
			}))

		# Reverse for cancellation
		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No', allow_negative_stock=allow_negative_stock)

	def get_stock_voucher_items(self, sle_map):
		return self.get("items") + self.get("packaging_items")

	def set_delivery_status(self, update=False, update_modified=True, validate_delivery=True):
		packed_qty_map = {}
		for d in self.get("items"):
			packed_qty_map[d.name] = flt(d.qty)

		delivered_qty_map = self.get_delivered_qty_map()

		if delivered_qty_map == packed_qty_map:
			self.is_delivered = 1
		else:
			self.is_delivered = 0

			if validate_delivery and delivered_qty_map:
				frappe.throw(_(
					"Some items from {0} are were not completely delivered. "
					"Partial delivery of Packing Slip is not allowed. "
					"Please select all items of Packing Slip."
				).format(frappe.get_desk_link("Packing Slip", self.name)))

		if update:
			self.db_set('is_delivered', self.is_delivered, update_modified=update_modified)

	def get_delivered_qty_map(self):
		if self.is_new():
			return {}

		delivered_by_dn = frappe.db.sql("""
			select packing_slip_item, sum(qty) as delivered_qty
			from `tabDelivery Note Item`
			where packing_slip = %s and docstatus = 1
			group by packing_slip_item
		""", self.name, as_dict=1)

		delivered_by_sinv = frappe.db.sql("""
			select i.packing_slip_item, sum(i.qty) as delivered_qty
			from `tabSales Invoice Item` i
			inner join `tabSales Invoice` s on s.name = i.parent
			where i.packing_slip = %s and s.docstatus = 1 and s.update_stock = 1
			group by i.packing_slip_item
		""", self.name, as_dict=1)

		delivered_qty_map = {}
		for d in delivered_by_dn + delivered_by_sinv:
			delivered_qty_map.setdefault(d.packing_slip_item, 0)
			delivered_qty_map[d.packing_slip_item] += d.delivered_qty

		return delivered_qty_map

	def set_status(self, update=False, status=None, update_modified=True):
		previous_status = self.status

		if self.docstatus == 0:
			self.status = "Draft"
		elif self.docstatus == 1:
			if not cint(self.is_delivered):
				self.status = "In Stock"
			else:
				self.status = "Delivered"
		else:
			self.status = "Cancelled"

		self.add_status_comment(previous_status)

		if update:
			self.db_set("status", self.status, update_modified=update_modified)


@frappe.whitelist()
def get_package_type_details(package_type, args):
	if isinstance(args, str):
		args = json.loads(args)

	packaging_items_copy_fields = [
		"item_code", "item_name", "description",
		"qty", "uom", "conversion_factor", "stock_qty",
		"tare_weight_per_unit"
	]

	package_type_doc = frappe.get_cached_doc("Package Type", package_type)
	if package_type_doc.weight_uom:
		args["weight_uom"] = package_type_doc.weight_uom

	args["child_doctype"] = "Packing Slip Packaging Material"

	packaging_items = []
	for d in package_type_doc.get("packaging_items"):
		if d.get("item_code"):
			item_row = {k: d.get(k) for k in packaging_items_copy_fields}

			item_args = args.copy()
			item_args.update(item_row)

			item_details = get_item_details(item_args)
			item_row.update(item_details)

			packaging_items.append(item_row)

	return {
		"packaging_items": packaging_items,
		"weight_uom": package_type_doc.weight_uom,
	}


@frappe.whitelist()
def get_item_details(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	if not args.item_code:
		frappe.throw(_("Item Code is mandatory"))

	item = frappe.get_cached_doc("Item", args.item_code)

	# Basic Item Details
	out.item_name = item.item_name
	out.description = item.description
	out.hide_item_code = get_hide_item_code(item, args)
	out.has_batch_no = item.has_batch_no
	out.has_serial_no = item.has_serial_no

	# Qty and UOM
	out.qty = flt(args.qty) or 1
	out.stock_uom = item.stock_uom
	if not args.get('uom'):
		args.uom = item.stock_uom

	if args.uom == item.stock_uom:
		out.uom = args.uom
		out.conversion_factor = 1
	else:
		conversion = get_conversion_factor(item.name, args.uom)
		if conversion.get('not_convertible'):
			out.uom = item.stock_uom
			out.conversion_factor = 1
		else:
			out.uom = args.uom
			out.conversion_factor = flt(conversion.get("conversion_factor"))

	out.stock_qty = out.qty * out.conversion_factor

	# Weight Per Unit
	out.net_weight_per_unit = flt(args.net_weight_per_unit) or get_weight_per_unit(item.name,
		weight_uom=args.weight_uom or item.weight_uom)
	out.tare_weight_per_unit = flt(args.tare_weight_per_unit) or get_weight_per_unit(item.name,
		weight_uom=args.weight_uom or item.weight_uom, weight_field="tare_weight_per_unit")

	# Warehouse
	out.source_warehouse = get_default_source_warehouse(item, args)
	out.force_default_warehouse = get_force_default_warehouse(item, args)

	# Accounting
	if args.company:
		stock_adjustment_account = frappe.get_cached_value('Company', args.company, 'stock_adjustment_account')
		default_expense_account = get_default_expense_account(args.item_code, args)
		if args.child_doctype == "Packing Slip Item":
			out.expense_account = stock_adjustment_account or default_expense_account
		elif args.child_doctype == "Packing Slip Packaging Material":
			out.expense_account = default_expense_account

		out.cost_center = get_default_cost_center(args.item_code, args)

	return out


def get_default_source_warehouse(item, args):
	warehouse = args.get("source_warehouse")
	if not warehouse:
		parent_warehouse = args.get("default_source_warehouse")

		default_values = get_item_default_values(item, args)
		default_warehouse = default_values.get("default_warehouse")

		force_default_warehouse = get_force_default_warehouse(item, args)
		if force_default_warehouse:
			warehouse = default_warehouse
		else:
			warehouse = parent_warehouse or default_warehouse

		if not warehouse:
			warehouse = get_global_default_warehouse(args.get("company"))

	return warehouse


@frappe.whitelist()
def get_item_weights_per_unit(item_codes, weight_uom=None):
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)

	if not item_codes:
		return {}

	out = {}
	for item_code in item_codes:
		item_weight_uom = frappe.get_cached_value("Item", item_code, "weight_uom")
		out[item_code] = {
			"net_weight_per_unit": get_weight_per_unit(item_code, weight_uom=weight_uom or item_weight_uom),
			"tare_weight_per_unit": get_weight_per_unit(item_code, weight_uom=weight_uom or item_weight_uom,
				weight_field="tare_weight_per_unit"),
		}

	return out


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as make_delivery_note_from_sales_order,\
		get_item_mapper_for_delivery

	packing_slip = frappe.get_doc("Packing Slip", source_name)
	target_doc = map_target_document("Delivery Note", target_doc, packing_slip)

	# Map Sales Orders
	sales_orders = list(set([d.sales_order for d in packing_slip.get("items") if d.get("sales_order")]))
	sales_order_docs = {}
	for so in sales_orders:
		sales_order_docs[so] = frappe.get_doc("Sales Order", so)
		target_doc = make_delivery_note_from_sales_order(so, target_doc, skip_item_mapping=True)

	so_item_mapper = get_item_mapper_for_delivery(allow_duplicate=True)
	packing_slip_item_mapper = get_packing_slip_item_mapper("Delivery Note Item")

	# Map Packing Slip Items
	for ps_item in packing_slip.get("items"):
		if not mapper_item_condition(ps_item, target_doc):
			continue

		if ps_item.get("sales_order_item"):
			source_parent = sales_order_docs[ps_item.sales_order]
			source_row = frappe.get_doc("Sales Order Item", ps_item.sales_order_item)
			mapper = so_item_mapper
		else:
			source_parent = packing_slip
			source_row = ps_item
			mapper = packing_slip_item_mapper

		dn_item = map_child_doc(source_row, target_doc, mapper, source_parent)
		update_mapped_item(dn_item, packing_slip, ps_item)

	postprocess_mapped_document(target_doc)
	return target_doc


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as make_sales_invoice_from_sales_order, \
		get_item_mapper_for_invoice

	packing_slip = frappe.get_doc("Packing Slip", source_name)
	target_doc = map_target_document("Sales Invoice", target_doc, packing_slip)

	# Map Sales Orders
	sales_orders = list(set([d.sales_order for d in packing_slip.get("items") if d.get("sales_order")]))
	sales_order_docs = {}
	sales_order_mappers = {}
	for sales_order in sales_orders:
		sales_order_docs[sales_order] = frappe.get_doc("Sales Order", sales_order)
		sales_order_mappers[sales_order] = get_item_mapper_for_invoice(sales_order, allow_duplicate=True)
		target_doc = make_sales_invoice_from_sales_order(sales_order, target_doc, skip_item_mapping=True)

	packing_slip_item_mapper = get_packing_slip_item_mapper("Sales Invoice Item")

	# Map Packing Slip Items
	for ps_item in packing_slip.get("items"):
		if not mapper_item_condition(ps_item, target_doc):
			continue

		if ps_item.get("sales_order_item"):
			source_parent = sales_order_docs[ps_item.sales_order]
			source_row = frappe.get_doc("Sales Order Item", ps_item.sales_order_item)
			mapper = sales_order_mappers[ps_item.sales_order]
		else:
			source_parent = packing_slip
			source_row = ps_item
			mapper = packing_slip_item_mapper

		sinv_item = map_child_doc(source_row, target_doc, mapper, source_parent)
		update_mapped_item(sinv_item, packing_slip, ps_item)

	postprocess_mapped_document(target_doc)
	target_doc.update_stock = 1

	return target_doc


def map_target_document(target_doctype, target_doc, packing_slip):
	if isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))

	if not target_doc:
		target_doc = frappe.new_doc(target_doctype)

	if not target_doc.get("customer"):
		target_doc.customer = packing_slip.customer

	return target_doc


def get_packing_slip_item_mapper(target_doctype):
	return {
		"doctype": target_doctype,
		"field_no_map": [
			"expense_account",
			"cost_center",
		],
	}


def mapper_item_condition(ps_item, target_doc):
	if ps_item.name in [d.packing_slip_item for d in target_doc.get("items") if d.get("packing_slip_item")]:
		return False

	return True


def update_mapped_item(target, packing_slip, ps_item):
	target.packing_slip = packing_slip.name
	target.packing_slip_item = ps_item.name

	target.qty = ps_item.qty
	target.uom = ps_item.uom
	target.conversion_factor = ps_item.conversion_factor

	target.net_weight_per_unit = ps_item.net_weight_per_unit
	target.weight_uom = packing_slip.weight_uom

	target.warehouse = packing_slip.warehouse
	target.batch_no = ps_item.batch_no
	target.serial_no = ps_item.serial_no


def postprocess_mapped_document(target):
	target.run_method('set_missing_values')
	target.run_method('set_po_nos')
	target.run_method('calculate_taxes_and_totals')
