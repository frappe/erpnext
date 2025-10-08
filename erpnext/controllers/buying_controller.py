# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import ValidationError, _, msgprint
from frappe.contacts.doctype.address.address import render_address
from frappe.utils import cint, flt, getdate
from frappe.utils.data import nowtime

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget
from erpnext.accounts.party import get_party_details
from erpnext.buying.utils import update_last_purchase_rate, validate_for_items
from erpnext.controllers.sales_and_purchase_return import get_rate_for_return
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import get_incoming_rate


class QtyMismatchError(ValidationError):
	pass


class BuyingController(SubcontractingController):
	def __setup__(self):
		self.flags.ignore_permlevel_for_fields = ["buying_price_list", "price_list_currency"]

	def validate(self):
		self.set_rate_for_standalone_debit_note()

		super().validate()
		if getattr(self, "supplier", None) and not self.supplier_name:
			self.supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name")

		self.validate_items()
		self.set_qty_as_per_stock_uom()
		self.validate_stock_or_nonstock_items()
		self.validate_warehouse()
		self.validate_from_warehouse()
		self.set_supplier_address()
		self.validate_auto_repeat_subscription_dates()
		self.create_package_for_transfer()

		if self.doctype == "Purchase Invoice":
			self.validate_purchase_receipt_if_update_stock()

		if self.doctype == "Purchase Receipt" or (self.doctype == "Purchase Invoice" and self.update_stock):
			# self.validate_purchase_return()
			self.validate_rejected_warehouse()
			self.validate_accepted_rejected_qty()
			validate_for_items(self)

			# sub-contracting
			self.validate_for_subcontracting()
			if self.get("is_old_subcontracting_flow"):
				self.create_raw_materials_supplied()
			self.set_landed_cost_voucher_amount()

		if self.doctype in ("Purchase Receipt", "Purchase Invoice"):
			self.update_valuation_rate()
			self.set_serial_and_batch_bundle()

	def onload(self):
		super().onload()
		self.set_onload(
			"backflush_based_on",
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on"),
		)

		if self.docstatus == 1 and self.doctype in ["Purchase Receipt", "Purchase Invoice"]:
			self.set_onload(
				"allow_to_make_qc_after_submission",
				frappe.db.get_single_value(
					"Stock Settings", "allow_to_make_quality_inspection_after_purchase_or_delivery"
				),
			)

	def create_package_for_transfer(self) -> None:
		"""Create serial and batch package for Sourece Warehouse in case of inter transfer."""

		if self.is_internal_transfer() and (
			self.doctype == "Purchase Receipt" or (self.doctype == "Purchase Invoice" and self.update_stock)
		):
			field = "delivery_note_item" if self.doctype == "Purchase Receipt" else "sales_invoice_item"

			doctype = "Delivery Note Item" if self.doctype == "Purchase Receipt" else "Sales Invoice Item"

			ids = [d.get(field) for d in self.get("items") if d.get(field)]
			bundle_ids = {}
			if ids:
				for bundle in frappe.get_all(
					doctype, filters={"name": ("in", ids)}, fields=["serial_and_batch_bundle", "name"]
				):
					bundle_ids[bundle.name] = bundle.serial_and_batch_bundle

			if not bundle_ids:
				return

			for item in self.get("items"):
				if item.get(field) and not item.serial_and_batch_bundle and bundle_ids.get(item.get(field)):
					item.serial_and_batch_bundle = self.make_package_for_transfer(
						bundle_ids.get(item.get(field)),
						item.from_warehouse,
						type_of_transaction="Outward",
						do_not_submit=True,
						qty=item.qty,
					)
				elif (
					not self.is_new()
					and item.serial_and_batch_bundle
					and next(
						(
							old_item
							for old_item in self.get_doc_before_save().items
							if old_item.name == item.name and old_item.qty != item.qty
						),
						None,
					)
					and len(
						sabe := frappe.get_all(
							"Serial and Batch Entry",
							filters={"parent": item.serial_and_batch_bundle, "serial_no": ["is", "not set"]},
							pluck="name",
						)
					)
					== 1
				):
					frappe.set_value("Serial and Batch Entry", sabe[0], "qty", item.qty)

	def set_rate_for_standalone_debit_note(self):
		if self.get("is_return") and self.get("update_stock") and not self.return_against:
			for row in self.items:
				if row.rate <= 0:
					# override the rate with valuation rate
					row.rate = get_incoming_rate(
						{
							"item_code": row.item_code,
							"warehouse": row.warehouse,
							"posting_date": self.get("posting_date"),
							"posting_time": self.get("posting_time"),
							"qty": row.qty,
							"serial_and_batch_bundle": row.get("serial_and_batch_bundle"),
							"company": self.company,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"voucher_detail_no": row.name,
						},
						raise_error_if_no_rate=False,
					)

					row.discount_percentage = 0.0
					row.discount_amount = 0.0
					row.margin_rate_or_amount = 0.0

	def set_missing_values(self, for_validate=False):
		super().set_missing_values(for_validate)

		self.set_supplier_from_item_default()
		self.set_price_list_currency("Buying")

		# set contact and address details for supplier, if they are not mentioned
		if getattr(self, "supplier", None):
			self.update_if_missing(
				get_party_details(
					self.supplier,
					party_type="Supplier",
					doctype=self.doctype,
					company=self.company,
					party_address=self.get("supplier_address"),
					shipping_address=self.get("shipping_address"),
					dispatch_address=self.get("dispatch_address"),
					company_address=self.get("billing_address"),
					fetch_payment_terms_template=not self.get("ignore_default_payment_terms_template"),
					ignore_permissions=self.flags.ignore_permissions,
				)
			)

		self.set_missing_item_details(for_validate)

	def set_supplier_from_item_default(self):
		if self.meta.get_field("supplier") and not self.supplier:
			for d in self.get("items"):
				supplier = frappe.db.get_value(
					"Item Default", {"parent": d.item_code, "company": self.company}, "default_supplier"
				)
				if supplier:
					self.supplier = supplier
				else:
					item_group = frappe.db.get_value("Item", d.item_code, "item_group")
					supplier = frappe.db.get_value(
						"Item Default", {"parent": item_group, "company": self.company}, "default_supplier"
					)
					if supplier:
						self.supplier = supplier
					break

	def validate_stock_or_nonstock_items(self):
		if self.meta.get_field("taxes") and not self.get_stock_items() and not get_asset_items(self):
			msg = _('Tax Category has been changed to "Total" because all the Items are non-stock items')
			self.update_tax_category(msg)

	def update_tax_category(self, msg):
		tax_for_valuation = [
			d for d in self.get("taxes") if d.category in ["Valuation", "Valuation and Total"]
		]

		if tax_for_valuation:
			for d in tax_for_valuation:
				d.category = "Total"

			msgprint(msg)

	def set_landed_cost_voucher_amount(self):
		for d in self.get("items"):
			lc_voucher_data = frappe.db.sql(
				"""select sum(applicable_charges) as total_applicable_charges, cost_center
				from `tabLanded Cost Item`
				where docstatus = 1 and purchase_receipt_item = %s and receipt_document = %s
				group by cost_center""",
				(d.name, self.name),
			)

			if lc_voucher_data:
				d.landed_cost_voucher_amount = lc_voucher_data[0][0] or 0.0
				if not d.cost_center and lc_voucher_data[0][1]:
					d.db_set("cost_center", lc_voucher_data[0][1])
			else:
				d.landed_cost_voucher_amount = 0.0

	def validate_from_warehouse(self):
		for item in self.get("items"):
			if item.get("from_warehouse") and (item.get("from_warehouse") == item.get("warehouse")):
				frappe.throw(
					_("Row #{0}: Accepted Warehouse and Supplier Warehouse cannot be same").format(item.idx)
				)

			if item.get("from_warehouse") and self.get("is_subcontracted"):
				frappe.throw(
					_(
						"Row #{0}: Cannot select Supplier Warehouse while suppling raw materials to subcontractor"
					).format(item.idx)
				)

	def set_supplier_address(self):
		address_dict = {
			"supplier_address": "address_display",
			"shipping_address": "shipping_address_display",
			"dispatch_address": "dispatch_address_display",
			"billing_address": "billing_address_display",
		}

		for address_field, address_display_field in address_dict.items():
			if self.get(address_field):
				self.set(
					address_display_field, render_address(self.get(address_field), check_permissions=False)
				)

	def set_total_in_words(self):
		from frappe.utils import money_in_words

		if self.meta.get_field("base_in_words"):
			if self.meta.get_field("base_rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(self.base_rounded_total)
			else:
				amount = abs(self.base_grand_total)
			self.base_in_words = money_in_words(amount, self.company_currency)

		if self.meta.get_field("in_words"):
			if self.meta.get_field("rounded_total") and not self.is_rounded_total_disabled():
				amount = abs(self.rounded_total)
			else:
				amount = abs(self.grand_total)

			self.in_words = money_in_words(amount, self.currency)

	# update valuation rate
	def update_valuation_rate(self, reset_outgoing_rate=True):
		"""
		item_tax_amount is the total tax amount applied on that item
		stored for valuation

		TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_and_asset_items = []
		stock_and_asset_items = self.get_stock_items() + get_asset_items(self)

		stock_and_asset_items_qty, stock_and_asset_items_amount = 0, 0
		last_item_idx = 1
		for d in self.get("items"):
			if d.item_code and d.item_code in stock_and_asset_items:
				stock_and_asset_items_qty += flt(d.qty)
				stock_and_asset_items_amount += flt(d.base_net_amount)
				last_item_idx = d.idx

		total_valuation_amount = sum(
			flt(d.base_tax_amount_after_discount_amount)
			for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]
		)

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get("items")):
			if item.item_code and item.qty and item.item_code in stock_and_asset_items:
				item_proportion = (
					flt(item.base_net_amount) / stock_and_asset_items_amount
					if stock_and_asset_items_amount
					else flt(item.qty) / stock_and_asset_items_qty
				)

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(
						valuation_amount_adjustment, self.precision("item_tax_amount", item)
					)
				else:
					item.item_tax_amount = flt(
						item_proportion * total_valuation_amount, self.precision("item_tax_amount", item)
					)
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item)
				if flt(item.conversion_factor) == 0.0:
					item.conversion_factor = (
						get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0
					)

				net_rate = item.base_net_amount
				if item.sales_incoming_rate:  # for internal transfer
					net_rate = item.qty * item.sales_incoming_rate

				qty_in_stock_uom = flt(item.qty * item.conversion_factor)
				if self.get("is_old_subcontracting_flow"):
					item.rm_supp_cost = self.get_supplied_items_cost(item.name, reset_outgoing_rate)
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ item.rm_supp_cost
						+ flt(item.landed_cost_voucher_amount)
					) / qty_in_stock_uom
				else:
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ flt(item.landed_cost_voucher_amount)
						+ flt(item.get("amount_difference_with_purchase_invoice"))
					) / qty_in_stock_uom
			else:
				item.valuation_rate = 0.0
		update_regional_item_valuation_rate(self)

	def set_incoming_rate(self):
		"""
		Override item rate with incoming rate for internal stock transfer
		"""
		if self.doctype not in ("Purchase Receipt", "Purchase Invoice"):
			return

		if not (self.doctype == "Purchase Receipt" or self.get("update_stock")):
			return

		if cint(self.get("is_return")):
			# Get outgoing rate based on original item cost based on valuation method
			return

		if not self.is_internal_transfer():
			return

		self.set_sales_incoming_rate_for_internal_transfer()

		allow_at_arms_length_price = frappe.get_cached_value(
			"Stock Settings", None, "allow_internal_transfer_at_arms_length_price"
		)
		if allow_at_arms_length_price:
			return

		for d in self.get("items"):
			d.discount_percentage = 0.0
			d.discount_amount = 0.0
			d.margin_rate_or_amount = 0.0

			if d.rate == d.sales_incoming_rate:
				continue

			d.rate = d.sales_incoming_rate
			frappe.msgprint(
				_(
					"Row {0}: Item rate has been updated as per valuation rate since its an internal stock transfer"
				).format(d.idx),
				alert=1,
			)

	def set_sales_incoming_rate_for_internal_transfer(self):
		"""
		Set incoming rate from the sales transaction against which the
		purchase is made (internal transfer)
		"""
		ref_doctype_map = {
			"Purchase Receipt": "Delivery Note Item",
			"Purchase Invoice": "Sales Invoice Item",
		}

		ref_doctype = ref_doctype_map.get(self.doctype)
		for d in self.get("items"):
			if not d.get(frappe.scrub(ref_doctype)):
				posting_time = self.get("posting_time")
				if not posting_time:
					posting_time = nowtime()

				outgoing_rate = get_incoming_rate(
					{
						"item_code": d.item_code,
						"warehouse": d.get("from_warehouse"),
						"posting_date": self.get("posting_date") or self.get("transaction_date"),
						"posting_time": posting_time,
						"qty": -1 * flt(d.get("stock_qty")),
						"serial_and_batch_bundle": d.get("serial_and_batch_bundle"),
						"company": self.company,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"allow_zero_valuation": d.get("allow_zero_valuation"),
						"voucher_detail_no": d.name,
					},
					raise_error_if_no_rate=False,
				)

				d.sales_incoming_rate = flt(outgoing_rate * (d.conversion_factor or 1), d.precision("rate"))
			else:
				field = "incoming_rate" if self.get("is_internal_supplier") else "rate"
				d.sales_incoming_rate = flt(
					frappe.db.get_value(ref_doctype, d.get(frappe.scrub(ref_doctype)), field)
					* (d.conversion_factor or 1),
					d.precision("rate"),
				)

	def validate_for_subcontracting(self):
		if self.is_subcontracted and self.get("is_old_subcontracting_flow"):
			if self.doctype in ["Purchase Receipt", "Purchase Invoice"] and not self.supplier_warehouse:
				frappe.throw(_("Supplier Warehouse mandatory for sub-contracted {0}").format(self.doctype))

			for item in self.get("items"):
				if item in self.sub_contracted_items and not item.bom:
					frappe.throw(_("Please select BOM in BOM field for Item {0}").format(item.item_code))
			if self.doctype != "Purchase Order":
				return
			for row in self.get("supplied_items"):
				if not row.reserve_warehouse:
					msg = f"Reserved Warehouse is mandatory for the Item {frappe.bold(row.rm_item_code)} in Raw Materials supplied"
					frappe.throw(_(msg))
		else:
			for item in self.get("items"):
				if item.get("bom"):
					item.bom = None

	def set_qty_as_per_stock_uom(self):
		allow_to_edit_stock_qty = frappe.db.get_single_value(
			"Stock Settings", "allow_to_edit_stock_uom_qty_for_purchase"
		)

		for d in self.get("items"):
			if d.meta.get_field("stock_qty"):
				# Check if item code is present
				# Conversion factor should not be mandatory for non itemized items
				if not d.conversion_factor and d.item_code:
					frappe.throw(_("Row {0}: Conversion Factor is mandatory").format(d.idx))
				d.stock_qty = flt(d.qty) * flt(d.conversion_factor)

				if self.doctype == "Purchase Receipt" and d.meta.get_field("received_stock_qty"):
					# Set Received Qty in Stock UOM
					d.received_stock_qty = flt(d.received_qty) * flt(
						d.conversion_factor, d.precision("conversion_factor")
					)

				if allow_to_edit_stock_qty:
					d.stock_qty = flt(d.stock_qty, d.precision("stock_qty"))
					if d.get("received_stock_qty") and d.meta.get_field("received_stock_qty"):
						d.received_stock_qty = flt(d.received_stock_qty, d.precision("received_stock_qty"))

	def validate_purchase_return(self):
		for d in self.get("items"):
			if self.is_return and flt(d.rejected_qty) != 0:
				frappe.throw(_("Row #{0}: Rejected Qty can not be entered in Purchase Return").format(d.idx))

			# validate rate with ref PR

	# validate accepted and rejected qty
	def validate_accepted_rejected_qty(self):
		for d in self.get("items"):
			self.validate_negative_quantity(d, ["received_qty", "qty", "rejected_qty"])

			if not flt(d.received_qty) and (flt(d.qty) or flt(d.rejected_qty)):
				d.received_qty = flt(d.qty) + flt(d.rejected_qty)

			# Check Received Qty = Accepted Qty + Rejected Qty
			val = flt(d.qty) + flt(d.rejected_qty)
			if flt(val, d.precision("received_qty")) != flt(d.received_qty, d.precision("received_qty")):
				message = _(
					"Row #{0}: Received Qty must be equal to Accepted + Rejected Qty for Item {1}"
				).format(d.idx, d.item_code)
				frappe.throw(msg=message, title=_("Mismatch"), exc=QtyMismatchError)

	def validate_negative_quantity(self, item_row, field_list):
		if self.is_return:
			return

		item_row = item_row.as_dict()
		for fieldname in field_list:
			if flt(item_row[fieldname]) < 0:
				frappe.throw(
					_("Row #{0}: {1} can not be negative for item {2}").format(
						item_row["idx"],
						frappe.get_meta(item_row.doctype).get_label(fieldname),
						item_row["item_code"],
					)
				)

	def check_for_on_hold_or_closed_status(self, ref_doctype, ref_fieldname):
		for d in self.get("items"):
			if d.get(ref_fieldname):
				status = frappe.db.get_value(ref_doctype, d.get(ref_fieldname), "status")
				if status in ("Closed", "On Hold"):
					frappe.throw(_("{0} {1} is {2}").format(ref_doctype, d.get(ref_fieldname), status))

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for d in self.get("items"):
			if d.item_code not in stock_items:
				continue

			if d.warehouse:
				pr_qty = flt(flt(d.qty) * flt(d.conversion_factor), d.precision("stock_qty"))

				if pr_qty:
					if d.from_warehouse and (
						(not cint(self.is_return) and self.docstatus == 1)
						or (cint(self.is_return) and self.docstatus == 2)
					):
						serial_and_batch_bundle = d.get("serial_and_batch_bundle")
						if self.is_internal_transfer() and self.is_return and self.docstatus == 2:
							serial_and_batch_bundle = frappe.db.get_value(
								"Stock Ledger Entry",
								{"voucher_detail_no": d.name, "warehouse": d.from_warehouse},
								"serial_and_batch_bundle",
							)

						from_warehouse_sle = self.get_sl_entries(
							d,
							{
								"actual_qty": -1 * pr_qty,
								"warehouse": d.from_warehouse,
								"outgoing_rate": d.rate,
								"recalculate_rate": 1,
								"dependant_sle_voucher_detail_no": d.name,
								"serial_and_batch_bundle": serial_and_batch_bundle,
							},
						)

						sl_entries.append(from_warehouse_sle)

					type_of_transaction = "Inward"
					if self.docstatus == 2:
						type_of_transaction = "Outward"

					sle = self.get_sl_entries(
						d,
						{
							"actual_qty": flt(pr_qty),
							"serial_and_batch_bundle": (
								d.serial_and_batch_bundle
								if not self.is_internal_transfer()
								or self.is_return
								or (self.is_internal_transfer() and self.docstatus == 2)
								else self.get_package_for_target_warehouse(
									d, type_of_transaction=type_of_transaction
								)
							),
						},
					)

					if self.is_return:
						outgoing_rate = get_rate_for_return(
							self.doctype, self.name, d.item_code, self.return_against, item_row=d
						)

						sle.update(
							{
								"outgoing_rate": outgoing_rate,
								"recalculate_rate": 1,
								"serial_and_batch_bundle": d.serial_and_batch_bundle,
							}
						)
						if d.from_warehouse:
							sle.dependant_sle_voucher_detail_no = d.name
					else:
						sle.update(
							{
								"incoming_rate": d.valuation_rate,
								"recalculate_rate": 1
								if (self.is_subcontracted and (d.bom or d.get("fg_item"))) or d.from_warehouse
								else 0,
							}
						)
					sl_entries.append(sle)

					if d.from_warehouse and (
						(not cint(self.is_return) and self.docstatus == 2)
						or (cint(self.is_return) and self.docstatus == 1)
					):
						serial_and_batch_bundle = None
						if self.is_internal_transfer() and self.docstatus == 2:
							serial_and_batch_bundle = frappe.db.get_value(
								"Stock Ledger Entry",
								{"voucher_detail_no": d.name, "warehouse": d.warehouse},
								"serial_and_batch_bundle",
							)

						from_warehouse_sle = self.get_sl_entries(
							d,
							{
								"actual_qty": -1 * pr_qty,
								"warehouse": d.from_warehouse,
								"recalculate_rate": 1,
								"serial_and_batch_bundle": (
									self.get_package_for_target_warehouse(d, d.from_warehouse, "Inward")
									if self.is_internal_transfer() and self.is_return
									else serial_and_batch_bundle
								),
							},
						)

						sl_entries.append(from_warehouse_sle)

			if flt(d.rejected_qty) != 0:
				valuation_rate_for_rejected_item = 0.0
				if frappe.db.get_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials"):
					valuation_rate_for_rejected_item = d.valuation_rate
				sl_entries.append(
					self.get_sl_entries(
						d,
						{
							"warehouse": d.rejected_warehouse,
							"actual_qty": flt(
								flt(d.rejected_qty) * flt(d.conversion_factor), d.precision("stock_qty")
							),
							"incoming_rate": valuation_rate_for_rejected_item if not self.is_return else 0.0,
							"outgoing_rate": valuation_rate_for_rejected_item if self.is_return else 0.0,
							"serial_and_batch_bundle": d.rejected_serial_and_batch_bundle,
						},
					)
				)

		if self.get("is_old_subcontracting_flow"):
			self.make_sl_entries_for_supplier_warehouse(sl_entries)

		self.make_sl_entries(
			sl_entries,
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)

	def get_package_for_target_warehouse(self, item, warehouse=None, type_of_transaction=None) -> str:
		if not item.serial_and_batch_bundle:
			return ""

		if not warehouse:
			warehouse = item.warehouse

		return self.make_package_for_transfer(
			item.serial_and_batch_bundle, warehouse, type_of_transaction=type_of_transaction
		)

	def update_ordered_and_reserved_qty(self):
		po_map = {}
		for d in self.get("items"):
			if self.doctype == "Purchase Receipt" and d.purchase_order:
				po_map.setdefault(d.purchase_order, []).append(d.purchase_order_item)

			elif self.doctype == "Purchase Invoice" and d.purchase_order and d.po_detail:
				po_map.setdefault(d.purchase_order, []).append(d.po_detail)

		for po, po_item_rows in po_map.items():
			if po and po_item_rows:
				po_obj = frappe.get_doc("Purchase Order", po)

				if po_obj.status in ["Closed", "Cancelled"]:
					frappe.throw(
						_("{0} {1} is cancelled or closed").format(_("Purchase Order"), po),
						frappe.InvalidStatusError,
					)

				po_obj.update_ordered_qty(po_item_rows)
				if self.get("is_old_subcontracting_flow"):
					po_obj.update_reserved_qty_for_subcontract()

	def on_submit(self):
		if self.get("is_return"):
			return

		if self.doctype in [
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		] and not frappe.db.get_single_value("Buying Settings", "disable_last_purchase_rate"):
			update_last_purchase_rate(self, is_submit=1)

	def on_cancel(self):
		super().on_cancel()

		if self.get("is_return"):
			return

		if self.doctype in [
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		] and not frappe.db.get_single_value("Buying Settings", "disable_last_purchase_rate"):
			update_last_purchase_rate(self, is_submit=0)

	def validate_budget(self):
		if self.docstatus == 1:
			for data in self.get("items"):
				args = data.as_dict()
				args.update(
					{
						"doctype": self.doctype,
						"company": self.company,
						"posting_date": (
							self.schedule_date
							if self.doctype == "Material Request"
							else self.transaction_date
						),
					}
				)

				validate_expense_against_budget(args)

	def validate_schedule_date(self):
		if not self.get("items"):
			return

		if any(d.schedule_date for d in self.get("items")):
			# Select earliest schedule_date.
			self.schedule_date = min(
				d.schedule_date for d in self.get("items") if d.schedule_date is not None
			)

		if self.schedule_date:
			for d in self.get("items"):
				if not d.schedule_date:
					d.schedule_date = self.schedule_date

				if (
					d.schedule_date
					and self.transaction_date
					and getdate(d.schedule_date) < getdate(self.transaction_date)
				):
					frappe.throw(_("Row #{0}: Reqd by Date cannot be before Transaction Date").format(d.idx))
		else:
			frappe.throw(_("Please enter Reqd by Date"))

	def validate_items(self):
		# validate items to see if they have is_purchase_item or is_subcontracted_item enabled
		if self.doctype == "Material Request":
			return

		if self.get("is_old_subcontracting_flow"):
			validate_item_type(self, "is_sub_contracted_item", "subcontracted")
		else:
			validate_item_type(self, "is_purchase_item", "purchase")


def validate_item_type(doc, fieldname, message):
	# iterate through items and check if they are valid sales or purchase items
	items = [d.item_code for d in doc.items if d.item_code]

	# No validation check inase of creating transaction using 'Opening Invoice Creation Tool'
	if not items:
		return

	item_list = ", ".join(["%s" % frappe.db.escape(d) for d in items])

	invalid_items = [
		d[0]
		for d in frappe.db.sql(
			f"""
		select item_code from tabItem where name in ({item_list}) and {fieldname}=0
		""",
			as_list=True,
		)
	]

	if invalid_items:
		items = ", ".join([d for d in invalid_items])

		if len(invalid_items) > 1:
			error_message = _(
				"Following items {0} are not marked as {1} item. You can enable them as {1} item from its Item master"
			).format(items, message)
		else:
			error_message = _(
				"Following item {0} is not marked as {1} item. You can enable them as {1} item from its Item master"
			).format(items, message)

		frappe.throw(error_message)


def get_asset_items(doc):
	if doc.doctype not in ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]:
		return []

	return [d.item_code for d in doc.items if d.get("is_fixed_asset")]


@erpnext.allow_regional
def update_regional_item_valuation_rate(doc):
	pass
