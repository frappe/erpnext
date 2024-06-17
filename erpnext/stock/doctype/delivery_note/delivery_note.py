# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, flt

from erpnext.controllers.accounts_controller import get_taxes_and_charges, merge_taxes
from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.doctype.serial_no.serial_no import get_delivery_note_serial_no

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class DeliveryNote(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.delivery_note_item.delivery_note_item import DeliveryNoteItem
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		additional_discount_percentage: DF.Float
		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		amount_eligible_for_commission: DF.Currency
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		campaign: DF.Link | None
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.SmallText | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.SmallText | None
		dispatch_address_name: DF.Link | None
		driver: DF.Link | None
		driver_name: DF.Data | None
		excise_page: DF.Data | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		installation_status: DF.Literal[None]
		instructions: DF.Text | None
		inter_company_reference: DF.Link | None
		is_internal_customer: DF.Check
		is_return: DF.Check
		issue_credit_note: DF.Check
		items: DF.Table[DeliveryNoteItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		lr_date: DF.Date | None
		lr_no: DF.Data | None
		named_place: DF.Data | None
		naming_series: DF.Literal["MAT-DN-.YYYY.-", "MAT-DN-RET-.YYYY.-"]
		net_total: DF.Currency
		other_charges_calculation: DF.TextEditor | None
		packed_items: DF.Table[PackedItem]
		per_billed: DF.Percent
		per_installed: DF.Percent
		per_returned: DF.Percent
		pick_list: DF.Link | None
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.SmallText | None
		posting_date: DF.Date
		posting_time: DF.Time
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		print_without_amount: DF.Check
		project: DF.Link | None
		represents_company: DF.Link | None
		return_against: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		sales_partner: DF.Link | None
		sales_team: DF.Table[SalesTeam]
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		selling_price_list: DF.Link
		set_posting_time: DF.Check
		set_target_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		shipping_address: DF.SmallText | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		source: DF.Link | None
		status: DF.Literal["", "Draft", "To Bill", "Completed", "Return Issued", "Cancelled", "Closed"]
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		title: DF.Data | None
		total: DF.Currency
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transporter: DF.Link | None
		transporter_name: DF.Data | None
		vehicle_no: DF.Data | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Delivery Note Item",
				"target_dt": "Sales Order Item",
				"join_field": "so_detail",
				"target_field": "delivered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "per_delivered",
				"target_ref_field": "qty",
				"source_field": "qty",
				"percent_join_field": "against_sales_order",
				"status_field": "delivery_status",
				"keyword": "Delivered",
				"second_source_dt": "Sales Invoice Item",
				"second_source_field": "qty",
				"second_join_field": "so_detail",
				"overflow_type": "delivery",
				"second_source_extra_cond": """ and exists(select name from `tabSales Invoice`
				where name=`tabSales Invoice Item`.parent and update_stock = 1)""",
			},
			{
				"source_dt": "Delivery Note Item",
				"target_dt": "Sales Invoice Item",
				"join_field": "si_detail",
				"target_field": "delivered_qty",
				"target_parent_dt": "Sales Invoice",
				"target_ref_field": "qty",
				"source_field": "qty",
				"percent_join_field": "against_sales_invoice",
				"overflow_type": "delivery",
				"no_allowance": 1,
			},
		]
		if cint(self.is_return):
			self.status_updater.extend(
				[
					{
						"source_dt": "Delivery Note Item",
						"target_dt": "Sales Order Item",
						"join_field": "so_detail",
						"target_field": "returned_qty",
						"target_parent_dt": "Sales Order",
						"source_field": "-1 * qty",
						"second_source_dt": "Sales Invoice Item",
						"second_source_field": "-1 * qty",
						"second_join_field": "so_detail",
						"extra_cond": """ and exists (select name from `tabDelivery Note`
					where name=`tabDelivery Note Item`.parent and is_return=1)""",
						"second_source_extra_cond": """ and exists (select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and is_return=1 and update_stock=1)""",
					},
					{
						"source_dt": "Delivery Note Item",
						"target_dt": "Delivery Note Item",
						"join_field": "dn_detail",
						"target_field": "returned_qty",
						"target_parent_dt": "Delivery Note",
						"target_parent_field": "per_returned",
						"target_ref_field": "stock_qty",
						"source_field": "-1 * stock_qty",
						"percent_join_field_parent": "return_against",
					},
				]
			)

	def onload(self):
		if self.docstatus == 0:
			self.set_onload("has_unpacked_items", self.has_unpacked_items())

	def before_print(self, settings=None):
		def toggle_print_hide(meta, fieldname):
			df = meta.get_field(fieldname)
			if self.get("print_without_amount"):
				df.set("__print_hide", 1)
			else:
				df.delete_key("__print_hide")

		item_meta = frappe.get_meta("Delivery Note Item")
		print_hide_fields = {
			"parent": ["grand_total", "rounded_total", "in_words", "currency", "total", "taxes"],
			"items": ["rate", "amount", "discount_amount", "price_list_rate", "discount_percentage"],
		}

		for key, fieldname in print_hide_fields.items():
			for f in fieldname:
				toggle_print_hide(self.meta if key == "parent" else item_meta, f)

		super().before_print(settings)

	def set_actual_qty(self):
		for d in self.get("items"):
			if d.item_code and d.warehouse:
				actual_qty = frappe.db.sql(
					"""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""",
					(d.item_code, d.warehouse),
				)
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

	def so_required(self):
		"""check in manage account if sales order required or not"""
		if frappe.db.get_single_value("Selling Settings", "so_required") == "Yes":
			for d in self.get("items"):
				if not d.against_sales_order:
					frappe.throw(_("Sales Order required for Item {0}").format(d.item_code))

	def validate(self):
		self.validate_posting_time()
		super().validate()
		self.validate_references()
		self.set_status()
		self.so_required()
		self.validate_proj_cust()
		self.check_sales_order_on_hold_or_close("against_sales_order")
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_with_previous_doc()
		self.set_serial_and_batch_bundle_from_pick_list()

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

		make_packing_list(self)
		self.update_current_stock()

		if not self.installation_status:
			self.installation_status = "Not Installed"

		self.validate_against_stock_reservation_entries()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Sales Order": {
					"ref_dn_field": "against_sales_order",
					"compare_fields": [
						["customer", "="],
						["company", "="],
						["project", "="],
						["currency", "="],
					],
				},
				"Sales Order Item": {
					"ref_dn_field": "so_detail",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
				"Sales Invoice": {
					"ref_dn_field": "against_sales_invoice",
					"compare_fields": [
						["customer", "="],
						["company", "="],
						["project", "="],
						["currency", "="],
					],
				},
				"Sales Invoice Item": {
					"ref_dn_field": "si_detail",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if (
			cint(frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate"))
			and not self.is_return
			and not self.is_internal_customer
		):
			self.validate_rate_with_reference_doc(
				[
					["Sales Order", "against_sales_order", "so_detail"],
					["Sales Invoice", "against_sales_invoice", "si_detail"],
				]
			)

	def set_serial_and_batch_bundle_from_pick_list(self):
		from erpnext.stock.serial_batch_bundle import SerialBatchCreation

		if not self.pick_list:
			return

		for item in self.items:
			if item.pick_list_item and not item.serial_and_batch_bundle:
				filters = {
					"item_code": item.item_code,
					"voucher_type": "Pick List",
					"voucher_no": self.pick_list,
					"voucher_detail_no": item.pick_list_item,
				}

				bundle_id = frappe.db.get_value("Serial and Batch Bundle", filters, "name")

				if bundle_id:
					cls_obj = SerialBatchCreation(
						{
							"type_of_transaction": "Outward",
							"serial_and_batch_bundle": bundle_id,
							"item_code": item.get("item_code"),
							"warehouse": item.get("warehouse"),
						}
					)

					cls_obj.duplicate_package()

					item.serial_and_batch_bundle = cls_obj.serial_and_batch_bundle

	def validate_references(self):
		self.validate_sales_order_references()
		self.validate_sales_invoice_references()

	def validate_sales_order_references(self):
		err_msg = ""
		for item in self.items:
			if (item.against_sales_order and not item.so_detail) or (
				not item.against_sales_order and item.so_detail
			):
				if not item.against_sales_order:
					err_msg += (
						_("'Sales Order' reference ({1}) is missing in row {0}").format(
							frappe.bold(item.idx), frappe.bold("against_sales_order")
						)
						+ "<br>"
					)
				else:
					err_msg += (
						_("'Sales Order Item' reference ({1}) is missing in row {0}").format(
							frappe.bold(item.idx), frappe.bold("so_detail")
						)
						+ "<br>"
					)

		if err_msg:
			frappe.throw(err_msg, title=_("References to Sales Orders are Incomplete"))

	def validate_sales_invoice_references(self):
		err_msg = ""
		for item in self.items:
			if (item.against_sales_invoice and not item.si_detail) or (
				not item.against_sales_invoice and item.si_detail
			):
				if not item.against_sales_invoice:
					err_msg += (
						_("'Sales Invoice' reference ({1}) is missing in row {0}").format(
							frappe.bold(item.idx), frappe.bold("against_sales_invoice")
						)
						+ "<br>"
					)
				else:
					err_msg += (
						_("'Sales Invoice Item' reference ({1}) is missing in row {0}").format(
							frappe.bold(item.idx), frappe.bold("si_detail")
						)
						+ "<br>"
					)

		if err_msg:
			frappe.throw(err_msg, title=_("References to Sales Invoices are Incomplete"))

	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql(
				"""select name from `tabProject`
				where name = %s and (customer = %s or
					ifnull(customer,'')='')""",
				(self.project, self.customer),
			)
			if not res:
				frappe.throw(
					_("Customer {0} does not belong to project {1}").format(self.customer, self.project)
				)

	def validate_warehouse(self):
		super().validate_warehouse()

		for d in self.get_item_list():
			if not d["warehouse"] and frappe.get_cached_value("Item", d["item_code"], "is_stock_item") == 1:
				frappe.throw(_("Warehouse required for stock Item {0}").format(d["item_code"]))

	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get("items"):
				d.actual_qty = frappe.db.get_value(
					"Bin", {"item_code": d.item_code, "warehouse": d.warehouse}, "actual_qty"
				)

			for d in self.get("packed_items"):
				bin_qty = frappe.db.get_value(
					"Bin",
					{"item_code": d.item_code, "warehouse": d.warehouse},
					["actual_qty", "projected_qty"],
					as_dict=True,
				)
				if bin_qty:
					d.actual_qty = flt(bin_qty.actual_qty)
					d.projected_qty = flt(bin_qty.projected_qty)

	def on_submit(self):
		self.validate_packed_qty()
		self.update_pick_list_status()

		# Check for Approving Authority
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)

		# update delivered qty in sales order
		self.update_prevdoc_status()
		self.update_billing_status()

		self.update_stock_reservation_entries()

		if not self.is_return:
			self.check_credit_limit()
		elif self.issue_credit_note:
			self.make_return_invoice()

		for table_name in ["items", "packed_items"]:
			if not self.get(table_name):
				continue

			self.make_bundle_for_sales_purchase_return(table_name)
			self.make_bundle_using_old_serial_batch_fields(table_name)

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()

	def on_cancel(self):
		super().on_cancel()

		self.check_sales_order_on_hold_or_close("against_sales_order")
		self.check_next_docstatus()

		self.update_prevdoc_status()
		self.update_billing_status()

		self.update_stock_reservation_entries()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		self.update_stock_ledger()

		self.cancel_packing_slips()
		self.update_pick_list_status()

		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
		)

		self.delete_auto_created_batches()

	def update_stock_reservation_entries(self) -> None:
		"""Updates Delivered Qty in Stock Reservation Entries."""

		# Don't update Delivered Qty on Return.
		if self.is_return:
			return

		if self._action == "submit":
			for item in self.get("items"):
				# Skip if `Sales Order` or `Sales Order Item` reference is not set.
				if not item.against_sales_order or not item.so_detail:
					continue

				sre_list = frappe.db.get_all(
					"Stock Reservation Entry",
					{
						"docstatus": 1,
						"voucher_type": "Sales Order",
						"voucher_no": item.against_sales_order,
						"voucher_detail_no": item.so_detail,
						"warehouse": item.warehouse,
						"status": ["not in", ["Delivered", "Cancelled"]],
					},
					order_by="creation",
				)

				# Skip if no Stock Reservation Entries.
				if not sre_list:
					continue

				qty_to_deliver = item.stock_qty
				for sre in sre_list:
					if qty_to_deliver <= 0:
						break

					sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

					qty_can_be_deliver = 0
					if sre_doc.reservation_based_on == "Serial and Batch":
						sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
						if sre_doc.has_serial_no:
							delivered_serial_nos = [d.serial_no for d in sbb.entries]
							for entry in sre_doc.sb_entries:
								if entry.serial_no in delivered_serial_nos:
									entry.delivered_qty = 1  # Qty will always be 0 or 1 for Serial No.
									entry.db_update()
									qty_can_be_deliver += 1
									delivered_serial_nos.remove(entry.serial_no)
						else:
							delivered_batch_qty = {d.batch_no: -1 * d.qty for d in sbb.entries}
							for entry in sre_doc.sb_entries:
								if entry.batch_no in delivered_batch_qty:
									delivered_qty = min(
										(entry.qty - entry.delivered_qty), delivered_batch_qty[entry.batch_no]
									)
									entry.delivered_qty += delivered_qty
									entry.db_update()
									qty_can_be_deliver += delivered_qty
									delivered_batch_qty[entry.batch_no] -= delivered_qty
					else:
						# `Delivered Qty` should be less than or equal to `Reserved Qty`.
						qty_can_be_deliver = min(
							(sre_doc.reserved_qty - sre_doc.delivered_qty), qty_to_deliver
						)

					sre_doc.delivered_qty += qty_can_be_deliver
					sre_doc.db_update()

					# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
					sre_doc.update_status()

					# Update Reserved Stock in Bin.
					sre_doc.update_reserved_stock_in_bin()

					qty_to_deliver -= qty_can_be_deliver

		if self._action == "cancel":
			for item in self.get("items"):
				# Skip if `Sales Order` or `Sales Order Item` reference is not set.
				if not item.against_sales_order or not item.so_detail:
					continue

				sre_list = frappe.db.get_all(
					"Stock Reservation Entry",
					{
						"docstatus": 1,
						"voucher_type": "Sales Order",
						"voucher_no": item.against_sales_order,
						"voucher_detail_no": item.so_detail,
						"warehouse": item.warehouse,
						"status": ["in", ["Partially Delivered", "Delivered"]],
					},
					order_by="creation",
				)

				# Skip if no Stock Reservation Entries.
				if not sre_list:
					continue

				qty_to_undelivered = item.stock_qty
				for sre in sre_list:
					if qty_to_undelivered <= 0:
						break

					sre_doc = frappe.get_doc("Stock Reservation Entry", sre)

					qty_can_be_undelivered = 0
					if sre_doc.reservation_based_on == "Serial and Batch":
						sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
						if sre_doc.has_serial_no:
							serial_nos_to_undelivered = [d.serial_no for d in sbb.entries]
							for entry in sre_doc.sb_entries:
								if entry.serial_no in serial_nos_to_undelivered:
									entry.delivered_qty = 0  # Qty will always be 0 or 1 for Serial No.
									entry.db_update()
									qty_can_be_undelivered += 1
									serial_nos_to_undelivered.remove(entry.serial_no)
						else:
							batch_qty_to_undelivered = {d.batch_no: -1 * d.qty for d in sbb.entries}
							for entry in sre_doc.sb_entries:
								if entry.batch_no in batch_qty_to_undelivered:
									undelivered_qty = min(
										entry.delivered_qty, batch_qty_to_undelivered[entry.batch_no]
									)
									entry.delivered_qty -= undelivered_qty
									entry.db_update()
									qty_can_be_undelivered += undelivered_qty
									batch_qty_to_undelivered[entry.batch_no] -= undelivered_qty
					else:
						# `Qty to Undelivered` should be less than or equal to `Delivered Qty`.
						qty_can_be_undelivered = min(sre_doc.delivered_qty, qty_to_undelivered)

					sre_doc.delivered_qty -= qty_can_be_undelivered
					sre_doc.db_update()

					# Update Stock Reservation Entry `Status` based on `Delivered Qty`.
					sre_doc.update_status()

					# Update Reserved Stock in Bin.
					sre_doc.update_reserved_stock_in_bin()

					qty_to_undelivered -= qty_can_be_undelivered

	def validate_against_stock_reservation_entries(self):
		"""Validates if Stock Reservation Entries are available for the Sales Order Item reference."""

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_reserved_warehouses_for_voucher,
		)

		# Don't validate if Return
		if self.is_return:
			return

		for item in self.get("items"):
			# Skip if `Sales Order` or `Sales Order Item` reference is not set.
			if not item.against_sales_order or not item.so_detail:
				continue

			reserved_warehouses = get_sre_reserved_warehouses_for_voucher(
				"Sales Order", item.against_sales_order, item.so_detail
			)

			# Skip if stock is not reserved.
			if not reserved_warehouses:
				continue

			# Set `Warehouse` from SRE if not set.
			if not item.warehouse:
				item.warehouse = reserved_warehouses[0]
			else:
				# Throw if `Warehouse` not in Reserved Warehouses.
				if item.warehouse not in reserved_warehouses:
					msg = _("Row #{0}: Stock is reserved for item {1} in warehouse {2}.").format(
						item.idx,
						frappe.bold(item.item_code),
						frappe.bold(reserved_warehouses[0])
						if len(reserved_warehouses) == 1
						else _("{0} and {1}").format(
							frappe.bold(", ".join(reserved_warehouses[:-1])),
							frappe.bold(reserved_warehouses[-1]),
						),
					)
					frappe.throw(msg, title=_("Stock Reservation Warehouse Mismatch"))

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		if self.per_billed == 100:
			return

		extra_amount = 0
		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				filters={"parent": self.customer, "parenttype": "Customer", "company": self.company},
				fieldname="bypass_credit_limit_check",
			)
		)

		if bypass_credit_limit_check_at_sales_order:
			for d in self.get("items"):
				if not d.against_sales_invoice:
					validate_against_credit_limit = True
					extra_amount = self.base_grand_total
					break
		else:
			for d in self.get("items"):
				if not (d.against_sales_order or d.against_sales_invoice):
					validate_against_credit_limit = True
					break

		if validate_against_credit_limit:
			check_credit_limit(
				self.customer, self.company, bypass_credit_limit_check_at_sales_order, extra_amount
			)

	def validate_packed_qty(self):
		"""Validate that if packed qty exists, it should be equal to qty"""

		if frappe.db.exists("Packing Slip", {"docstatus": 1, "delivery_note": self.name}):
			product_bundle_list = self.get_product_bundle_list()
			for item in self.items + self.packed_items:
				if (
					item.item_code not in product_bundle_list
					and flt(item.packed_qty)
					and flt(item.packed_qty) != flt(item.qty)
				):
					frappe.throw(
						_("Row {0}: Packed Qty must be equal to {1} Qty.").format(
							item.idx, frappe.bold(item.doctype)
						)
					)

	def update_pick_list_status(self):
		from erpnext.stock.doctype.pick_list.pick_list import update_pick_list_status

		update_pick_list_status(self.pick_list)

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql(
			"""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.delivery_note = %s and t1.docstatus = 1""",
			(self.name),
		)
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} has already been submitted").format(submit_rv[0][0]))

		submit_in = frappe.db.sql(
			"""select t1.name
			from `tabInstallation Note` t1, `tabInstallation Note Item` t2
			where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""",
			(self.name),
		)
		if submit_in:
			frappe.throw(_("Installation Note {0} has already been submitted").format(submit_in[0][0]))

	def cancel_packing_slips(self):
		"""
		Cancel submitted packing slips related to this delivery note
		"""
		res = frappe.db.sql(
			"""SELECT name FROM `tabPacking Slip` WHERE delivery_note = %s
			AND docstatus = 1""",
			self.name,
		)

		if res:
			for r in res:
				ps = frappe.get_doc("Packing Slip", r[0])
				ps.cancel()
			frappe.msgprint(_("Packing Slip(s) cancelled"))

	def update_status(self, status):
		self.set_status(update=True, status=status)
		self.notify_update()
		clear_doctype_notifications(self)

	def update_billing_status(self, update_modified=True):
		updated_delivery_notes = [self.name]
		for d in self.get("items"):
			if d.si_detail and not d.so_detail:
				d.db_set("billed_amt", d.amount, update_modified=update_modified)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			dn_doc = self if (dn == self.name) else frappe.get_doc("Delivery Note", dn)
			dn_doc.update_billing_percentage(update_modified=update_modified)

		self.load_from_db()

	def make_return_invoice(self):
		try:
			return_invoice = make_sales_invoice(self.name)
			return_invoice.is_return = True
			return_invoice.save()
			return_invoice.submit()

			credit_note_link = frappe.utils.get_link_to_form("Sales Invoice", return_invoice.name)

			frappe.msgprint(_("Credit Note {0} has been created automatically").format(credit_note_link))
		except Exception:
			frappe.throw(
				_(
					"Could not create Credit Note automatically, please uncheck 'Issue Credit Note' and submit again"
				)
			)

	def has_unpacked_items(self):
		product_bundle_list = self.get_product_bundle_list()

		for item in self.items + self.packed_items:
			if item.item_code not in product_bundle_list and flt(item.packed_qty) < flt(item.qty):
				return True

		return False

	def get_product_bundle_list(self):
		items_list = [item.item_code for item in self.items]
		return frappe.db.get_all(
			"Product Bundle",
			filters={"new_item_code": ["in", items_list], "disabled": 0},
			pluck="name",
		)


def update_billed_amount_based_on_so(so_detail, update_modified=True):
	from frappe.query_builder.functions import Sum

	# Billed against Sales Order directly
	si_item = frappe.qb.DocType("Sales Invoice Item").as_("si_item")
	sum_amount = Sum(si_item.amount).as_("amount")

	billed_against_so = (
		frappe.qb.from_(si_item)
		.select(sum_amount)
		.where(
			(si_item.so_detail == so_detail)
			& ((si_item.dn_detail.isnull()) | (si_item.dn_detail == ""))
			& (si_item.docstatus == 1)
		)
		.run()
	)
	billed_against_so = billed_against_so and billed_against_so[0][0] or 0

	# Get all Delivery Note Item rows against the Sales Order Item row
	dn = frappe.qb.DocType("Delivery Note").as_("dn")
	dn_item = frappe.qb.DocType("Delivery Note Item").as_("dn_item")

	dn_details = (
		frappe.qb.from_(dn)
		.from_(dn_item)
		.select(dn_item.name, dn_item.amount, dn_item.si_detail, dn_item.parent)
		.where(
			(dn.name == dn_item.parent)
			& (dn_item.so_detail == so_detail)
			& (dn.docstatus == 1)
			& (dn.is_return == 0)
		)
		.orderby(dn.posting_date, dn.posting_time, dn.name)
		.run(as_dict=True)
	)

	updated_dn = []
	for dnd in dn_details:
		billed_amt_agianst_dn = 0

		# If delivered against Sales Invoice
		if dnd.si_detail:
			billed_amt_agianst_dn = flt(dnd.amount)
			billed_against_so -= billed_amt_agianst_dn
		else:
			# Get billed amount directly against Delivery Note
			billed_amt_agianst_dn = frappe.db.sql(
				"""select sum(amount) from `tabSales Invoice Item`
				where dn_detail=%s and docstatus=1""",
				dnd.name,
			)
			billed_amt_agianst_dn = billed_amt_agianst_dn and billed_amt_agianst_dn[0][0] or 0

		# Distribute billed amount directly against SO between DNs based on FIFO
		if billed_against_so and billed_amt_agianst_dn < dnd.amount:
			pending_to_bill = flt(dnd.amount) - billed_amt_agianst_dn
			if pending_to_bill <= billed_against_so:
				billed_amt_agianst_dn += pending_to_bill
				billed_against_so -= pending_to_bill
			else:
				billed_amt_agianst_dn += billed_against_so
				billed_against_so = 0

		frappe.db.set_value(
			"Delivery Note Item",
			dnd.name,
			"billed_amt",
			billed_amt_agianst_dn,
			update_modified=update_modified,
		)

		updated_dn.append(dnd.parent)

	return updated_dn


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Shipments"),
		}
	)
	return list_context


def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql(
		"""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""",
		delivery_note,
	):
		if not invoiced_qty_map.get(dn_detail):
			invoiced_qty_map[dn_detail] = 0
		invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map


def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(
		frappe.db.sql(
			"""select dn_item.dn_detail, abs(dn_item.qty) as qty
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
	""",
			delivery_note,
		)
	)

	return returned_qty_map


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, args=None):
	doc = frappe.get_doc("Delivery Note", source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been Invoiced/Returned"))

		if args and args.get("merge_taxes"):
			merge_taxes(source.get("taxes") or [], target)

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = to_make_invoice_qty_map[source_doc.name]

		if source_doc.serial_no and source_parent.per_billed > 0 and not source_parent.is_return:
			target_doc.serial_no = get_delivery_note_serial_no(
				source_doc.item_code, target_doc.qty, source_parent.name
			)

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.name, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.name, 0))
			returned_qty_map[item_row.name] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty

	doc = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Sales Invoice",
				"field_map": {"is_return": "is_return"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "dn_detail",
					"parent": "delivery_note",
					"so_detail": "so_detail",
					"against_sales_order": "sales_order",
					"serial_no": "serial_no",
					"cost_center": "cost_center",
				},
				"postprocess": update_item,
				"filter": lambda d: get_pending_qty(d) <= 0
				if not doc.get("is_return")
				else get_pending_qty(d) > 0,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"add_if_empty": True,
				"ignore": args.get("merge_taxes") if args else 0,
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"field_map": {"incentives": "incentives"},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doc.set_payment_schedule()

	return doc


@frappe.whitelist()
def make_delivery_trip(source_name, target_doc=None, kwargs=None):
	def update_stop_details(source_doc, target_doc, source_parent):
		target_doc.customer = source_parent.customer
		target_doc.address = source_parent.shipping_address_name
		target_doc.customer_address = source_parent.shipping_address
		target_doc.contact = source_parent.contact_person
		target_doc.customer_contact = source_parent.contact_display
		target_doc.grand_total = source_parent.grand_total

		# Append unique Delivery Notes in Delivery Trip
		delivery_notes.append(target_doc.delivery_note)

	delivery_notes = []

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {"doctype": "Delivery Trip", "validation": {"docstatus": ["=", 1]}},
			"Delivery Note Item": {
				"doctype": "Delivery Stop",
				"field_map": {"parent": "delivery_note"},
				"condition": lambda item: item.parent not in delivery_notes,
				"postprocess": update_stop_details,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_installation_note(source_name, target_doc=None, kwargs=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.installed_qty)
		target.serial_no = obj.serial_no

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {"doctype": "Installation Note", "validation": {"docstatus": ["=", 1]}},
			"Delivery Note Item": {
				"doctype": "Installation Note Item",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.installed_qty < doc.qty,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_packing_slip(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.packed_qty)

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Packing Slip",
				"field_map": {"name": "delivery_note", "letter_head": "letter_head"},
				"validation": {"docstatus": ["=", 0]},
			},
			"Delivery Note Item": {
				"doctype": "Packing Slip Item",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"batch_no": "batch_no",
					"description": "description",
					"qty": "qty",
					"stock_uom": "stock_uom",
					"name": "dn_detail",
				},
				"postprocess": update_item,
				"condition": lambda item: (
					not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code, "disabled": 0})
					and flt(item.packed_qty) < flt(item.qty)
				),
			},
			"Packed Item": {
				"doctype": "Packing Slip Item",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"batch_no": "batch_no",
					"description": "description",
					"qty": "qty",
					"name": "pi_detail",
				},
				"postprocess": update_item,
				"condition": lambda item: (flt(item.packed_qty) < flt(item.qty)),
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_shipment(source_name, target_doc=None):
	def postprocess(source, target):
		user = frappe.db.get_value(
			"User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"], as_dict=1
		)
		target.pickup_contact_email = user.email
		pickup_contact_display = f"{user.full_name}"
		if user:
			if user.email:
				pickup_contact_display += "<br>" + user.email
			if user.phone:
				pickup_contact_display += "<br>" + user.phone
			if user.mobile_no and not user.phone:
				pickup_contact_display += "<br>" + user.mobile_no
		target.pickup_contact = pickup_contact_display

		# As we are using session user details in the pickup_contact then pickup_contact_person will be session user
		target.pickup_contact_person = frappe.session.user

		contact = frappe.db.get_value(
			"Contact", source.contact_person, ["email_id", "phone", "mobile_no"], as_dict=1
		)
		delivery_contact_display = f"{source.contact_display}"
		if contact:
			if contact.email_id:
				delivery_contact_display += "<br>" + contact.email_id
			if contact.phone:
				delivery_contact_display += "<br>" + contact.phone
			if contact.mobile_no and not contact.phone:
				delivery_contact_display += "<br>" + contact.mobile_no
		target.delivery_contact = delivery_contact_display

		if source.shipping_address_name:
			target.delivery_address_name = source.shipping_address_name
			target.delivery_address = source.shipping_address
		elif source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

	doclist = get_mapped_doc(
		"Delivery Note",
		source_name,
		{
			"Delivery Note": {
				"doctype": "Shipment",
				"field_map": {
					"grand_total": "value_of_goods",
					"company": "pickup_company",
					"company_address": "pickup_address_name",
					"company_address_display": "pickup_address",
					"customer": "delivery_customer",
					"contact_person": "delivery_contact_name",
					"contact_email": "delivery_contact_email",
				},
				"validation": {"docstatus": ["=", 1]},
			},
			"Delivery Note Item": {
				"doctype": "Shipment Delivery Note",
				"field_map": {
					"name": "prevdoc_detail_docname",
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"base_amount": "grand_total",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Delivery Note", source_name, target_doc)


@frappe.whitelist()
def update_delivery_note_status(docname, status):
	dn = frappe.get_doc("Delivery Note", docname)
	dn.update_status(status)


@frappe.whitelist()
def make_inter_company_purchase_receipt(source_name, target_doc=None):
	return make_inter_company_transaction("Delivery Note", source_name, target_doc)


def make_inter_company_transaction(doctype, source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
		get_inter_company_details,
		set_purchase_references,
		update_address,
		update_taxes,
		validate_inter_company_transaction,
	)

	if doctype == "Delivery Note":
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Receipt"
		source_document_warehouse_field = "target_warehouse"
		target_document_warehouse_field = "from_warehouse"
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Delivery Note"
		source_document_warehouse_field = "from_warehouse"
		target_document_warehouse_field = "target_warehouse"

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

		if target.doctype == "Purchase Receipt":
			master_doctype = "Purchase Taxes and Charges Template"
		else:
			master_doctype = "Sales Taxes and Charges Template"

		if not target.get("taxes") and target.get("taxes_and_charges"):
			for tax in get_taxes_and_charges(master_doctype, target.get("taxes_and_charges")):
				target.append("taxes", tax)

		if not target.get("items"):
			frappe.throw(_("All items have already been received"))

	def update_details(source_doc, target_doc, source_parent):
		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype == "Purchase Receipt":
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
			target_doc.is_internal_supplier = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			update_address(target_doc, "supplier_address", "address_display", source_doc.company_address)
			update_address(
				target_doc, "shipping_address", "shipping_address_display", source_doc.customer_address
			)
			update_address(
				target_doc, "billing_address", "billing_address_display", source_doc.customer_address
			)

			update_taxes(
				target_doc,
				party=target_doc.supplier,
				party_type="Supplier",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address,
			)
		else:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.company_address = source_doc.supplier_address
			target_doc.selling_price_list = source_doc.buying_price_list
			target_doc.is_internal_customer = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			update_address(
				target_doc, "company_address", "company_address_display", source_doc.supplier_address
			)
			update_address(
				target_doc, "shipping_address_name", "shipping_address", source_doc.shipping_address
			)
			update_address(target_doc, "customer_address", "address_display", source_doc.shipping_address)

			update_taxes(
				target_doc,
				party=target_doc.customer,
				party_type="Customer",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.customer_address,
				company_address=target_doc.company_address,
				shipping_address_name=target_doc.shipping_address_name,
			)

	def update_item(source, target, source_parent):
		if source_parent.doctype == "Delivery Note" and source.received_qty:
			target.qty = flt(source.qty) + flt(source.returned_qty) - flt(source.received_qty)

		if source.get("use_serial_batch_fields"):
			target.set("use_serial_batch_fields", 1)

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": target_doctype,
				"postprocess": update_details,
				"field_no_map": ["taxes_and_charges", "set_warehouse"],
			},
			doctype + " Item": {
				"doctype": target_doctype + " Item",
				"field_map": {
					source_document_warehouse_field: target_document_warehouse_field,
					"name": "delivery_note_item",
					"purchase_order": "purchase_order",
					"purchase_order_item": "purchase_order_item",
					"material_request": "material_request",
					"Material_request_item": "material_request_item",
				},
				"field_no_map": ["warehouse"],
				"condition": lambda item: item.received_qty < item.qty + item.returned_qty,
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist
