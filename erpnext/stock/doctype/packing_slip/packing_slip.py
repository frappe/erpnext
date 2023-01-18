# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, cstr, combine_datetime
from frappe.model.mapper import map_child_doc, get_mapped_doc
from erpnext.controllers.stock_controller import StockController
from erpnext.stock.get_item_details import get_conversion_factor, get_hide_item_code, get_weight_per_unit,\
	get_default_expense_account, get_default_cost_center, get_item_default_values, get_force_default_warehouse,\
	get_global_default_warehouse
from erpnext.stock.utils import get_incoming_rate
from erpnext.accounts.party import validate_party_frozen_disabled
import json


force_item_fields = ["stock_uom", "has_batch_no", "has_serial_no", "force_default_warehouse"]


class PackingSlip(StockController):
	item_table_fields = ["items", "packaging_items"]

	def get_feed(self):
		return _("Packed {0}").format(self.get("package_type"))

	def onload(self):
		super().onload()
		if self.docstatus == 0:
			self.calculate_totals()

	def validate(self):
		self.validate_posting_time()
		super(PackingSlip, self).validate()
		self.validate_items()
		self.validate_source_packing_slips()
		self.validate_sales_orders()
		self.validate_unpack_against()
		self.validate_with_previous_doc()
		self.validate_customer()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.calculate_totals()
		self.validate_weights()
		self.set_cost_percentage()
		self.set_title()
		self.set_status(validate=False)

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
		self.set_source_packing_slips()

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
						if f in force_item_fields or item.get(f) in ("", None):
							item.set(f, item_details.get(f))

	def set_source_packing_slips(self):
		# Packing Slips from items table
		contents_packing_slips = []
		for d in self.get("items"):
			if d.get("source_packing_slip") and d.source_packing_slip not in contents_packing_slips:
				contents_packing_slips.append(d.source_packing_slip)

		# Remove
		packing_slips_visited = set()
		to_remove = []
		for d in self.get("packing_slips"):
			# remove if not in items
			if not d.source_packing_slip or d.source_packing_slip not in contents_packing_slips:
				to_remove.append(d)
				continue

			# remove if duplicate
			if d.source_packing_slip in packing_slips_visited:
				to_remove.append(d)

			packing_slips_visited.add(d.source_packing_slip)

		for d in to_remove:
			self.remove(d)

		# Add missing Packing Slips
		packages_packing_slips = [d.source_packing_slip for d in self.get("packing_slips") if d.get("source_packing_slip")]
		for source_packing_slips in contents_packing_slips:
			if source_packing_slips not in packages_packing_slips:
				new_row = self.append("packing_slips")
				new_row.source_packing_slip = source_packing_slips

		# Set details
		self.set_packing_slip_values()

	def set_packing_slip_values(self):
		for d in self.get("packing_slips"):
			details = frappe.db.get_value("Packing Slip", d.source_packing_slip,
				["package_type", "total_net_weight", "total_tare_weight", "total_gross_weight"], as_dict=1)

			if details:
				d.source_package_type = details.package_type
				d.net_weight = details.total_net_weight
				d.tare_weight = details.total_tare_weight
				d.gross_weight = details.total_gross_weight

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

					if self.is_unpack:
						if flt(d.qty) > 0:
							frappe.throw(_("Row #{0}: Item {1}, quantity must be negative number for unpacking")
							.format(d.idx, frappe.bold(d.item_code)))
					else:
						if flt(d.qty) < 0:
							frappe.throw(_("Row #{0}: Item {1}, quantity must be positive number")
								.format(d.idx, frappe.bold(d.item_code)))

	def validate_weights(self):
		weight_fields = ["net_weight", "tare_weight", "gross_weight"]

		for table_field in self.item_table_fields:
			for d in self.get(table_field):
				for weight_field in weight_fields:
					if self.is_unpack:
						if d.meta.has_field(weight_field) and flt(d.get(weight_field)) > 0:
							frappe.throw(_("Row #{0}: {1} must be negative for unpacking").format(
								d.idx, d.meta.get_label(weight_field)
							))
					else:
						if d.meta.has_field(weight_field) and flt(d.get(weight_field)) < 0:
							frappe.throw(_("Row #{0}: {1} cannot be negative").format(
								d.idx, d.meta.get_label(weight_field)
							))

		if self.is_unpack:
			if flt(self.total_tare_weight) > 0:
				frappe.throw(_("Total Tare Weight must be negative for unpacking"))
			if flt(self.total_gross_weight) > 0:
				frappe.throw(_("Total Gross Weight must be negative for unpacking"))
		else:
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

	def validate_with_previous_doc(self):
		super(PackingSlip, self).validate_with_previous_doc({
			"Sales Order Item": {
				"ref_dn_field": "sales_order_item",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
			},
			"Packing Slip Item": {
				"ref_dn_field": "packing_slip_item",
				"compare_fields": [
					["item_code", "="], ["uom", "="], ["conversion_factor", "="],
					["batch_no", "="], ["serial_no", "="],
				],
				"is_child_table": True,
			},
		})

		if self.get("is_unpack"):
			super(PackingSlip, self).validate_with_previous_doc({
				"Packing Slip Item": {
					"ref_dn_field": "unpack_against_row",
					"compare_fields": [
						["item_code", "="], ["uom", "="], ["conversion_factor", "="],
						["batch_no", "="], ["serial_no", "="],
					],
					"is_child_table": True,
				},
			})

			super(PackingSlip, self).validate_with_previous_doc({
				"Packing Slip Packaging Material": {
					"ref_dn_field": "unpack_against_row",
					"compare_fields": [
						["item_code", "="], ["batch_no", "="],
					],
					"is_child_table": True,
				},
			}, table_doctype="Packing Slip Packaging Material")

	def validate_source_packing_slips(self):
		def get_packing_slip_details(name):
			if not packing_slip_map.get(name):
				packing_slip_map[name] = frappe.db.get_value("Packing Slip", name, [
					"name", "docstatus", "status",
					"company", "customer", "project", "weight_uom",
					"posting_date", "posting_time"
				], as_dict=1)

			return packing_slip_map[name]

		packing_slip_map = {}

		# Validate Packing Slips
		for d in self.get("items"):
			if d.get("source_packing_slip"):
				if d.source_packing_slip == self.name:
					frappe.throw(_("Row #{0}: Source Packing Slip cannot be the same as the Target Packing Slip"))

				packing_slip = get_packing_slip_details(d.source_packing_slip)
				if not packing_slip:
					frappe.throw(_("Row #{0}: Packing Slip {1} does not exist").format(d.source_packing_slip))

				if packing_slip.docstatus == 0:
					frappe.throw(_("Row #{0}: Source {1} is in draft").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name)
					))
				if packing_slip.docstatus == 2:
					frappe.throw(_("Row #{0}: Source {1} is cancelled").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name)
					))

				if (packing_slip.status != "In Stock" and not self.is_unpack) or (packing_slip.status != "Nested" and self.is_unpack):
					frappe.throw(_("Row #{0}: Cannot select Source {1} because its status is {2}").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name), frappe.bold(packing_slip.status)
					))

				if self.company != packing_slip.company:
					frappe.throw(_("Row #{0}: Company does not match with Source {1}. Company must be {2}").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name), frappe.bold(packing_slip.company)
					))

				if cstr(self.project) != cstr(packing_slip.project):
					frappe.throw(_("Row #{0}: Project does not match with Source {1}. Project must be {2}").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name), frappe.bold(packing_slip.project)
					))

				if packing_slip.customer and self.customer != packing_slip.customer:
					frappe.throw(_("Row #{0}: Customer does not match with Source {1}. Customer must be {2}").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name), frappe.bold(packing_slip.customer)
					))

				if self.weight_uom != packing_slip.weight_uom:
					frappe.throw(_("Row #{0}: Weight UOM does not match with Source {1}. Weight UOM must be {2}").format(
						d.idx, frappe.get_desk_link("Packing Slip", packing_slip.name), frappe.bold(packing_slip.weight_uom)
					))

				source_packing_dt = combine_datetime(packing_slip.posting_date, packing_slip.posting_time)
				nested_packing_dt = combine_datetime(self.posting_date, self.posting_time)
				if nested_packing_dt < source_packing_dt:
					frappe.throw(_("Row #{0}: Nested Packing Date/Time cannot be before Source {1} Date/Time {2}").format(
						d.idx,
						frappe.get_desk_link("Packing Slip", packing_slip.name),
						frappe.bold(frappe.format(source_packing_dt))
					))

				# Validate Packing Slip Item
				if not d.packing_slip_item:
					frappe.throw(_("Row #{0}: Missing Source Packing Slip Row Reference").format(d.idx))

				packing_slip_item = frappe.db.get_value("Packing Slip Item", d.packing_slip_item,
					['qty', 'net_weight', 'tare_weight', 'gross_weight'], as_dict=1)

				if not packing_slip_item:
					frappe.throw(_("Row #{0}: Invalid Source Packing Slip Row Reference").format(d.idx))

				if self.is_unpack:
					packing_slip_item.qty *= -1
					packing_slip_item.net_weight *= -1
					packing_slip_item.tare_weight *= -1
					packing_slip_item.gross_weight *= -1

				if flt(d.qty) != packing_slip_item.qty:
					frappe.throw(_("Row #{0}: Qty does not match with Source {1}. Qty must be {2}").format(
						d.idx,
						frappe.get_desk_link("Packing Slip", packing_slip.name),
						frappe.bold(frappe.format(packing_slip_item.qty))
					))

				if flt(d.net_weight) != packing_slip_item.net_weight:
					frappe.throw(_("Row #{0}: Net Weight does not match with Source {1}. Net Weight must be {2}").format(
						d.idx,
						frappe.get_desk_link("Packing Slip", packing_slip.name),
						frappe.bold(frappe.format(packing_slip_item.net_weight))
					))
				if flt(d.tare_weight) != packing_slip_item.tare_weight:
					frappe.throw(_("Row #{0}: Tare Weight does not match with Source {1}. Tare Weight must be {2}").format(
						d.idx,
						frappe.get_desk_link("Packing Slip", packing_slip.name),
						frappe.bold(frappe.format(packing_slip_item.tare_weight))
					))
				if flt(d.gross_weight) != packing_slip_item.gross_weight:
					frappe.throw(_("Row #{0}: Gross Weight does not match with Source {1}. Gross Weight must be {2}").format(
						d.idx,
						frappe.get_desk_link("Packing Slip", packing_slip.name),
						frappe.bold(frappe.format(packing_slip_item.gross_weight))
					))

	def validate_sales_orders(self):
		sales_orders = list(set([d.sales_order for d in self.get("items") if d.get("sales_order")]))
		sales_order_map = {}
		for sales_order in sales_orders:
			details = frappe.db.get_value("Sales Order", sales_order,
				["name", "docstatus", "status", "company", "customer", "customer_name", "project"], as_dict=1)
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

			if self.company != order_details.company:
				frappe.throw(_("Row #{0}: {1} Company {2} does not match with Packing Slip").format(
					d.idx, frappe.get_desk_link("Sales Order", order_details.name), frappe.bold(order_details.company)
				))

			if cstr(self.project) != cstr(order_details.project):
				frappe.throw(_("Row #{0}: {1} Project {2} does not match with Packing Slip").format(
					d.idx, frappe.get_desk_link("Sales Order", order_details.name), frappe.bold(order_details.project)
				))

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

	def validate_unpack_against(self):
		if not self.get("is_unpack"):
			return

		if not self.get("unpack_against"):
			frappe.throw(_("Missing Unpack Against Packing Slip"))

		unpack_against = frappe.db.get_value("Packing Slip", self.unpack_against, [
			"name", "docstatus", "status",
			"company", "customer", "package_type", "warehouse",
			"posting_date", "posting_time"
		], as_dict=1)

		if not unpack_against:
			frappe.throw(_("Unpack Against Packing Slip {0} does not exist").format(frappe.bold(self.unpack_against)))

		if unpack_against.docstatus != 1:
			frappe.throw(_("Unpack Against {0} is not submitted").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name)
			))

		if unpack_against.status != "In Stock":
			frappe.throw(_("Cannot Unpack Against {0} because its status is {1}").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name), frappe.bold(unpack_against.status)
			))

		if self.company != unpack_against.company:
			frappe.throw(_("Company does not match with Unpack Against {0}. Company must be {1}").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name), frappe.bold(unpack_against.company)
			))

		if unpack_against.customer and self.customer != unpack_against.customer:
			frappe.throw(_("Customer does not match with Unpack Against {0}. Customer must be {1}").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name), frappe.bold(unpack_against.customer)
			))

		if self.package_type != unpack_against.package_type:
			frappe.throw(_("Package Type does not match with Unpack Against {0}. Package Type must be {1}").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name), frappe.bold(unpack_against.package_type)
			))

		if self.warehouse != unpack_against.warehouse:
			frappe.throw(_("Target Warehouse does not match with Unpack Against {0}. Target Warehouse must be {1}").format(
				frappe.get_desk_link("Packing Slip", unpack_against.name), frappe.bold(unpack_against.warehouse)
			))

		unpack_against_dt = combine_datetime(unpack_against.posting_date, unpack_against.posting_time)
		self_dt = combine_datetime(self.posting_date, self.posting_time)
		if self_dt < unpack_against_dt:
			frappe.throw(_("Unpacking Date/Time cannot be before Packing Date/Time {0}").format(frappe.format(self_dt)))

		for d in self.get("items"):
			if not d.get("unpack_against_row"):
				frappe.throw(_("Row #{0}: Missing Unpack Against Row Reference").format(d.idx))

			unpacked_against_row = frappe.db.get_value("Packing Slip Item", d.unpack_against_row,
				['qty', 'net_weight', 'tare_weight', 'gross_weight'], as_dict=1)

			if not unpacked_against_row:
				frappe.throw(_("Row #{0}: Invalid Unpack Against Row Reference").format(d.idx))

			unpacked_against_row.qty *= -1
			unpacked_against_row.net_weight *= -1
			unpacked_against_row.tare_weight *= -1
			unpacked_against_row.gross_weight *= -1

			if flt(d.qty) != unpacked_against_row.qty:
				frappe.throw(_("Row #{0}: Qty does not match with Unpack Against {1}. Qty must be {2}").format(
					d.idx,
					frappe.get_desk_link("Packing Slip", unpack_against.name),
					frappe.bold(frappe.format(unpacked_against_row.qty))
				))

			if flt(d.net_weight) != unpacked_against_row.net_weight:
				frappe.throw(_("Row #{0}: Net Weight does not match with Unpack Against {1}. Net Weight must be {2}").format(
					d.idx,
					frappe.get_desk_link("Packing Slip", unpack_against.name),
					frappe.bold(frappe.format(unpacked_against_row.net_weight))
				))
			if flt(d.tare_weight) != unpacked_against_row.tare_weight:
				frappe.throw(_("Row #{0}: Tare Weight does not match with Unpack Against {1}. Tare Weight must be {2}").format(
					d.idx,
					frappe.get_desk_link("Packing Slip", unpack_against.name),
					frappe.bold(frappe.format(unpacked_against_row.tare_weight))
				))
			if flt(d.gross_weight) != unpacked_against_row.gross_weight:
				frappe.throw(_("Row #{0}: Gross Weight does not match with Unpack Against {1}. Gross Weight must be {2}").format(
					d.idx,
					frappe.get_desk_link("Packing Slip", unpack_against.name),
					frappe.bold(frappe.format(unpacked_against_row.gross_weight))
				))

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

				if not item.get("source_packing_slip"):
					self.total_net_weight += flt(item.get("net_weight"))
					self.total_tare_weight += flt(item.get("tare_weight"))

		for d in self.get("packing_slips"):
			if self.is_unpack:
				self.total_net_weight -= d.net_weight
				self.total_tare_weight -= d.tare_weight
			else:
				self.total_net_weight += d.net_weight
				self.total_tare_weight += d.tare_weight

		self.round_floats_in(self, ['total_net_weight', 'total_tare_weight'])
		self.total_gross_weight = flt(self.total_net_weight + self.total_tare_weight, self.precision("total_gross_weight"))

	def set_cost_percentage(self):
		total_cost = 0
		total_stock_qty = 0

		for d in self.get("items"):
			args = self.get_args_for_incoming_rate(d)
			d.valuation_rate = get_incoming_rate(args, raise_error_if_no_rate=False)
			d.valuation_amount = flt(d.valuation_rate) * flt(d.stock_qty)

			total_cost += d.valuation_amount
			total_stock_qty += flt(d.stock_qty)

		for d in self.get("items"):
			if total_cost:
				d.cost_percentage = d.valuation_amount / total_cost * 100
			else:
				d.cost_percentage = flt(d.stock_qty) / total_stock_qty * 100 if total_stock_qty else 0

	def get_args_for_incoming_rate(self, item):
		return frappe._dict({
			"item_code": item.item_code,
			"warehouse": item.source_warehouse,
			"batch_no": item.batch_no,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"qty": -1 * flt(item.stock_qty),
			"serial_no": item.get("serial_no"),
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"company": self.company,
			"allow_zero_valuation": cint(item.get("allow_zero_valuation_rate")),
		})

	def update_previous_doc_status(self):
		sales_orders = set()
		sales_order_row_names = set()
		packing_slips = set()

		for d in self.items:
			# Get non nested sales orders from items
			if not d.get("source_packing_slip"):
				if d.sales_order:
					sales_orders.add(d.sales_order)
				if d.sales_order_item:
					sales_order_row_names.add(d.sales_order_item)

			# Get nested from
			if d.source_packing_slip:
				packing_slips.add(d.source_packing_slip)

		for name in sales_orders:
			doc = frappe.get_doc("Sales Order", name)
			doc.set_packing_status(update=True)
			doc.validate_packed_qty(from_doctype=self.doctype, row_names=sales_order_row_names)
			doc.notify_update()

		if self.is_unpack and self.unpack_against:
			packing_slips.add(self.unpack_against)

		for name in packing_slips:
			doc = frappe.get_doc("Packing Slip", name)
			doc.set_status(update=True)
			doc.notify_update()

	def update_stock_ledger(self, allow_negative_stock=False):
		sl_entries = []

		# Packaging Material
		self.get_packaging_material_sles(sl_entries)

		# Package Contents Transfer between Packing Slip
		if not self.is_unpack:
			self.get_packing_transfer_sles(sl_entries)
		else:
			self.get_unpack_transfer_sles(sl_entries)

		# Reverse for cancellation
		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No', allow_negative_stock=allow_negative_stock)

	def get_packaging_material_sles(self, sl_entries):
		for d in self.get("packaging_items"):
			# OUT SLE for packaging material (or IN for Unpack)
			sle_material = self.get_sl_entries(d, {
				"warehouse": d.source_warehouse,
				"actual_qty": -flt(d.stock_qty),
			})

			# Unpack IN at same rate
			if self.is_unpack and d.unpack_against_row and self.docstatus == 1:
				sle_material.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": self.unpack_against,
					"dependent_voucher_detail_no": d.unpack_against_row,
					"dependency_type": "Amount",
				}]

			sl_entries.append(sle_material)

	def get_packing_transfer_sles(self, sl_entries):
		for d in self.get("items"):
			# OUT SLE for items contents source warehouse
			sle_out = self.get_sl_entries(d, {
				"warehouse": d.source_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"packing_slip": d.get("source_packing_slip"),
			})

			if d.get("source_packing_slip") and d.get("packing_slip_item") and self.docstatus == 1:
				# Transfer Dependency
				sle_out.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": d.source_packing_slip,
					"dependent_voucher_detail_no": d.packing_slip_item,
					"dependency_type": "Amount",
					"dependency_qty_filter": "Positive",
				}]

			sl_entries.append(sle_out)

			# IN SLE for item contents target warehouse
			sle_in = self.get_sl_entries(d, {
				"warehouse": self.warehouse,
				"actual_qty": flt(d.stock_qty),
				"packing_slip": self.name,
			})

			if self.docstatus == 1:
				# Transfer Dependency
				sle_in.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": self.name,
					"dependent_voucher_detail_no": d.name,
					"dependency_type": "Amount",
				}]

				# Include Consumed Packaging Material in Valaution
				for dep_row in self.get("packaging_items"):
					if flt(dep_row.stock_qty):
						sle_in.dependencies.append({
							"dependent_voucher_type": self.doctype,
							"dependent_voucher_no": self.name,
							"dependent_voucher_detail_no": dep_row.name,
							"dependency_type": "Amount",
							"dependency_percentage": d.cost_percentage
						})

			sl_entries.append(sle_in)

	def get_unpack_transfer_sles(self, sl_entries):
		for d in self.get("items"):
			# Unpack OUT SLE for items contents target warehouse
			sle_out = self.get_sl_entries(d, {
				"warehouse": self.warehouse,
				"actual_qty": flt(d.stock_qty),
				"packing_slip": self.unpack_against,
			})

			# Unpack OUT at same rate
			if self.docstatus == 1 and d.unpack_against_row:
				sle_out.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": self.unpack_against,
					"dependent_voucher_detail_no": d.unpack_against_row,
					"dependency_type": "Amount",
					"dependency_qty_filter": "Positive",
				}]

			sl_entries.append(sle_out)

			# Unpack IN SLE for item contents source warehouse
			sle_in = self.get_sl_entries(d, {
				"warehouse": d.source_warehouse,
				"actual_qty": -flt(d.stock_qty),
				"packing_slip": d.get("source_packing_slip"),
			})

			if self.docstatus == 1:
				# Transfer Dependency
				sle_in.dependencies = [{
					"dependent_voucher_type": self.doctype,
					"dependent_voucher_no": self.name,
					"dependent_voucher_detail_no": d.name,
					"dependency_type": "Amount",
				}]

				# Include Packaging Material in Cost
				for dep_row in self.get("packaging_items"):
					if flt(dep_row.stock_qty):
						sle_in.dependencies.append({
							"dependent_voucher_type": self.doctype,
							"dependent_voucher_no": self.name,
							"dependent_voucher_detail_no": dep_row.name,
							"dependency_type": "Amount",
							"dependency_percentage": d.cost_percentage
						})

			sl_entries.append(sle_in)

	def get_stock_voucher_items(self, sle_map):
		return self.get("items") + self.get("packaging_items")

	def set_status(self, update=False, status=None, update_modified=True, validate=True):
		previous_status = self.status

		is_nested = 0
		is_unpacked = 0
		is_delivered = 0

		# Packed
		packed_qty_map = {}
		for d in self.get("items"):
			packed_qty_map[d.name] = flt(d.qty)

		# Nested
		nested_qty_map = self.get_nested_qty_map()
		if nested_qty_map == packed_qty_map:
			is_nested = 1
		elif validate and nested_qty_map:
			self.raise_incomplete_fulfilment("nested", "nesting")

		# Unpacked
		unpacked_qty_map = self.get_unpacked_qty_map()
		if unpacked_qty_map == packed_qty_map:
			is_unpacked = 1
		elif validate and unpacked_qty_map:
			self.raise_incomplete_fulfilment("unpacked", "unpacking")

		# Delivered
		delivered_qty_map = self.get_delivered_qty_map()
		if delivered_qty_map == packed_qty_map:
			is_delivered = 1
		elif validate and delivered_qty_map:
			self.raise_incomplete_fulfilment("delivered", "delivery")

		if self.docstatus == 0:
			self.status = "Draft"
		elif self.docstatus == 1:
			if is_delivered:
				self.status = "Delivered"
			elif is_unpacked or cint(self.is_unpack):
				self.status = "Unpacked"
			elif is_nested:
				self.status = "Nested"
			else:
				self.status = "In Stock"
		else:
			self.status = "Cancelled"

		self.add_status_comment(previous_status)

		if update:
			self.db_set("status", self.status, update_modified=update_modified)

	def get_delivered_qty_map(self):
		if self.is_new():
			return {}

		delivered_by_dn = frappe.db.sql("""
			select packing_slip_item, sum(qty) as delivered_qty
			from `tabDelivery Note Item`
			where packing_slip = %s and docstatus = 1
			group by packing_slip_item
			having delivered_qty != 0
		""", self.name, as_dict=1)

		delivered_by_sinv = frappe.db.sql("""
			select i.packing_slip_item, sum(i.qty) as delivered_qty
			from `tabSales Invoice Item` i
			inner join `tabSales Invoice` s on s.name = i.parent
			where i.packing_slip = %s and s.docstatus = 1 and s.update_stock = 1
			group by i.packing_slip_item
			having delivered_qty != 0
		""", self.name, as_dict=1)

		delivered_qty_map = {}
		for d in delivered_by_dn + delivered_by_sinv:
			delivered_qty_map.setdefault(d.packing_slip_item, 0)
			delivered_qty_map[d.packing_slip_item] += d.delivered_qty

		return delivered_qty_map

	def get_nested_qty_map(self):
		if self.is_new():
			return {}

		nested_qty_map = dict(frappe.db.sql("""
			select i.packing_slip_item, sum(i.qty) as nested_qty
			from `tabPacking Slip Item` i
			inner join `tabPacking Slip` s on s.name = i.parent
			where i.source_packing_slip = %s and s.docstatus = 1
			group by i.packing_slip_item
			having nested_qty != 0
		""", self.name))

		return nested_qty_map

	def get_unpacked_qty_map(self):
		if self.is_new():
			return {}

		unpacked_qty_map = dict(frappe.db.sql("""
			select i.unpack_against_row, sum(-i.qty) as unpacked_qty
			from `tabPacking Slip Item` i
			inner join `tabPacking Slip` s on s.name = i.parent
			where s.unpack_against = %s and s.docstatus = 1
			group by i.unpack_against_row
		""", self.name))

		return unpacked_qty_map

	def raise_incomplete_fulfilment(self, past, present):
		frappe.throw(_(
			"Some items from {packing_slip} are were not completely {past}. "
			"Partial {present} of Package is not allowed. "
			"Please select all items of Packing Slip."
		).format(
			packing_slip=frappe.get_desk_link("Packing Slip", self.name),
			past=_(past),
			present=_(present),
		))


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
		out.expense_account = stock_adjustment_account or get_default_expense_account(args.item_code, args)
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
def make_target_packing_slip(source_name, target_doc=None):
	source_packing_slip = frappe.get_doc("Packing Slip", source_name)
	target_doc = map_target_document("Packing Slip", target_doc, source_packing_slip)

	packing_slip_item_mapper = {
		"doctype": "Packing Slip Item",
		"field_map": {
			"parent": "source_packing_slip",
			"name": "packing_slip_item",
			"sales_order": "sales_order",
			"sales_order_item": "sales_order_item",
			"batch_no": "batch_no",
			"serial_no": "serial_no",
		},
		"field_no_map": [
			"source_warehouse",
			"expense_account",
			"cost_center",
		]
	}

	# Map Packing Slip Items
	for ps_item in source_packing_slip.get("items"):
		if not mapper_item_condition(ps_item, target_doc):
			continue

		target_row = map_child_doc(ps_item, target_doc, packing_slip_item_mapper, source_packing_slip)
		target_row.source_warehouse = source_packing_slip.warehouse

	target_doc.run_method('set_missing_values')
	target_doc.run_method('calculate_totals')
	return target_doc


@frappe.whitelist()
def make_unpack_packing_slip(source_name, target_doc=None):
	def update_item(source_doc, target_doc, source_parent, target_parent):
		target_doc.qty = -1 * source_doc.qty

	def update_material(source_doc, target_doc, source_parent, target_parent):
		target_doc.qty = -1 * source_doc.qty

	def postprocess(source, target):
		target.is_unpack = 1
		target.run_method('set_missing_values')
		target.run_method('calculate_totals')

	unpack_packing_slip = get_mapped_doc("Packing Slip", source_name, {
		"Packing Slip": {
			"doctype": "Packing Slip",
			"validation": {
				"docstatus": ["=", 1],
			},
			"field_map": {
				"name": "unpack_against",
				"warehouse": "warehouse",
				"package_type": "package_type",
			}
		},
		"Packing Slip Item": {
			"doctype": "Packing Slip Item",
			"field_map": {
				"name": "unpack_against_row",
				"source_packing_slip": "source_packing_slip",
				"packing_slip_item": "packing_slip_item",
				"sales_order": "sales_order",
				"sales_order_item": "sales_order_item",
				"batch_no": "batch_no",
				"serial_no": "serial_no",
				"source_warehouse": "source_warehouse",
			},
			"postprocess": update_item
		},
		"Packing Slip Packaging Material": {
			"doctype": "Packing Slip Packaging Material",
			"field_map": {
				"name": "unpack_against_row",
				"batch_no": "batch_no",
				"serial_no": "serial_no",
				"source_warehouse": "source_warehouse",
			},
			"postprocess": update_material
		}
	}, target_doc, postprocess)

	return unpack_packing_slip


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
		update_mapped_delivery_item(dn_item, packing_slip, ps_item)

	postprocess_mapped_delivery_document(target_doc)
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
		update_mapped_delivery_item(sinv_item, packing_slip, ps_item)

	postprocess_mapped_delivery_document(target_doc)
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


def mapper_item_condition(ps_item, target_doc):
	if ps_item.name in [d.packing_slip_item for d in target_doc.get("items") if d.get("packing_slip_item")]:
		return False

	return True


def get_packing_slip_item_mapper(target_doctype):
	return {
		"doctype": target_doctype,
		"field_no_map": [
			"expense_account",
			"cost_center",
		],
	}


def update_mapped_delivery_item(target, packing_slip, ps_item):
	target.packing_slip = packing_slip.name
	target.packing_slip_item = ps_item.name

	target.sales_order = ps_item.sales_order
	target.sales_order_item = ps_item.sales_order_item

	target.qty = ps_item.qty
	target.uom = ps_item.uom
	target.conversion_factor = ps_item.conversion_factor

	target.net_weight_per_unit = ps_item.net_weight_per_unit
	target.weight_uom = packing_slip.weight_uom

	target.warehouse = packing_slip.warehouse
	target.batch_no = ps_item.batch_no
	target.serial_no = ps_item.serial_no


def postprocess_mapped_delivery_document(target):
	target.run_method('set_missing_values')
	target.run_method('set_po_nos')
	target.run_method('calculate_taxes_and_totals')
