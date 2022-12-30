# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.get_item_details import get_conversion_factor, get_hide_item_code, get_weight_per_unit,\
	get_default_expense_account, get_default_cost_center
import json


force_item_fields = ['stock_uom', 'has_batch_no', 'has_serial_no']


class PackingSlip(StockController):
	item_table_fields = ['items', 'packing_items']

	def get_feed(self):
		return _("Packed {0}").format(self.get("package_type"))

	def validate(self):
		self.validate_posting_time()
		super(PackingSlip, self).validate()
		self.validate_target_handling_unit()
		self.validate_contents_mandatory()
		self.validate_items()
		self.validate_handling_units()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.calculate_totals()
		self.validate_weights()

	def before_submit(self):
		self.create_handling_unit()

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

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

	def validate_target_handling_unit(self):
		if self.handling_unit:
			hu = frappe.db.get_value("Handling Unit", self.handling_unit, ['name', 'status', 'package_type'], as_dict=1)
			if not hu:
				frappe.throw(_("Target Handling Unit {0} does not exist").format(self.handling_unit))

			if hu.status not in ["Inactive", "In Stock"]:
				frappe.throw(_("Cannot pack into Target {0} because its status is {1}")
					.format(frappe.get_desk_link("Handling Unit", hu.name), frappe.bold(hu.status)))

			if hu.package_type and self.package_type != hu.package_type:
				frappe.throw(_("Package Type does not match with Target {0}")
					.format(frappe.get_desk_link("Handling Unit", hu.name)))

	def validate_contents_mandatory(self):
		if not self.get("items") and not self.get("handling_units"):
			frappe.throw(_("Please enter Packed Items or Packed Handling Units"))

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

	def validate_handling_units(self):
		pass

	def validate_weights(self):
		for field in self.item_table_fields:
			for d in self.get(field):
				if flt(d.total_weight) < 0:
					frappe.throw(_("Row #{0}: {1} cannot be negative").format(d.idx, d.meta.get_label('total_weight')))

		if flt(self.total_tare_weight) < 0:
			frappe.throw(_("Total Tare Weight cannot be negative"))

		if flt(self.total_gross_weight) < 0:
			frappe.throw(_("Total Gross Weight cannot be negative"))

	def validate_warehouse(self):
		from erpnext.stock.utils import validate_warehouse_company

		warehouses = []
		if self.from_warehouse:
			warehouses.append(self.from_warehouse)
		if self.to_warehouse:
			warehouses.append(self.to_warehouse)

		warehouses = list(set(warehouses))
		for w in warehouses:
			validate_warehouse_company(w, self.company)

	def calculate_totals(self):
		self.total_net_weight = 0
		if not self.manual_tare_weight:
			self.total_tare_weight = 0

		for field in self.item_table_fields:
			for item in self.get(field):
				self.round_floats_in(item, excluding=['weight_per_unit'])
				item.stock_qty = item.qty * item.conversion_factor
				item.total_weight = flt(item.weight_per_unit * item.stock_qty, item.precision("total_weight"))

				if item.doctype == "Packing Slip Item":
					self.total_net_weight += item.total_weight
				elif item.doctype == "Packing Slip Packing Material":
					if not self.manual_tare_weight:
						self.total_tare_weight += item.total_weight

		for item in self.get("handling_units"):
			self.total_net_weight += item.net_weight
			if not self.manual_tare_weight:
				self.total_tare_weight += item.tare_weight

		self.round_floats_in(self, ['total_net_weight', 'total_tare_weight'])
		self.total_gross_weight = flt(self.total_net_weight + self.total_tare_weight, self.precision("total_gross_weight"))

	def create_handling_unit(self):
		if self.handling_unit:
			return

		hu_doc = frappe.new_doc("Handling Unit")
		hu_doc.package_type = self.package_type
		hu_doc.package_uom = self.package_uom
		hu_doc.insert(ignore_permissions=True)

		self.handling_unit = hu_doc.name

	def update_stock_ledger(self, allow_negative_stock=False):
		sl_entries = []

		# SLE for items contents source warehouse
		for d in self.get('items'):
			sl_entries.append(self.get_sl_entries(d, {
				"warehouse": self.from_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"incoming_rate": 0
			}))

		# SLE for item contents target warehouse
		for d in self.get('items'):
			sle = self.get_sl_entries(d, {
				"warehouse": self.to_warehouse,
				"actual_qty": flt(d.stock_qty),
				"handling_unit": self.handling_unit,
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

		# SLE for packing material
		for d in self.get('packing_items'):
			sl_entries.append(self.get_sl_entries(d, {
				"warehouse": self.from_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"incoming_rate": 0
			}))

		# Reverse for cancellation
		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No', allow_negative_stock=allow_negative_stock)

	def get_stock_voucher_items(self, sle_map):
		return self.get("items") + self.get("packing_items")


@frappe.whitelist()
def get_package_type_details(package_type):
	packing_items_copy_fields = [
		"item_code", "item_name", "description",
		"qty", "uom", "conversion_factor", "stock_qty",
		"weight_per_unit"
	]

	package_type_doc = frappe.get_cached_doc("Package Type", package_type)
	packing_items = []
	for d in package_type_doc.get("packing_items"):
		packing_items.append({k: d.get(k) for k in packing_items_copy_fields})

	return {
		"packing_items": packing_items,
		"manual_tare_weight": cint(package_type_doc.manual_tare_weight),
		"total_tare_weight": flt(package_type_doc.total_tare_weight),
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

	# Net Weight
	out.weight_per_unit = get_weight_per_unit(item.name, weight_uom=args.weight_uom or item.weight_uom)

	# Accounting
	if args.company:
		stock_adjustment_account = frappe.get_cached_value('Company', args.company, 'stock_adjustment_account')
		default_expense_account = get_default_expense_account(args.item_code, args)
		if args.child_doctype == "Packing Slip Item":
			out.expense_account = stock_adjustment_account or default_expense_account
		elif args.child_doctype == "Packing Slip Packing Material":
			out.expense_account = default_expense_account

		out.cost_center = get_default_cost_center(args.item_code, args)

	return out


@frappe.whitelist()
def get_item_weights_per_unit(item_codes, weight_uom=None):
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)

	if not item_codes:
		return {}

	out = {}
	for item_code in item_codes:
		item_weight_uom = frappe.get_cached_value("Item", item_code, "weight_uom")
		out[item_code] = get_weight_per_unit(item_code, weight_uom=weight_uom or item_weight_uom)

	return out
