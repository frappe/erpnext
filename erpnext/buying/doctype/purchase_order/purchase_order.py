# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.party import get_party_account_currency
from erpnext.buying.doctype.purchase_order.services.drop_ship import DropShipService
from erpnext.buying.doctype.purchase_order.services.status import StatusService
from erpnext.buying.doctype.purchase_order.services.subcontracting import SubcontractingService
from erpnext.buying.utils import validate_for_items
from erpnext.controllers.buying_controller import BuyingController
from erpnext.controllers.status_updater import get_allowance_for
from erpnext.manufacturing.doctype.blanket_order.blanket_order import (
	validate_against_blanket_order,
)
from erpnext.stock.doctype.item.item import get_last_purchase_details
from erpnext.stock.stock_balance import get_ordered_qty, update_bin_qty

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class PurchaseOrder(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import (
			PurchaseTaxesandCharges,
		)
		from erpnext.buying.doctype.purchase_order_item.purchase_order_item import PurchaseOrderItem

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		advance_paid: DF.Currency
		advance_payment_status: DF.Literal["Not Initiated", "Initiated", "Partially Paid", "Fully Paid"]
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_taxes_and_charges_added: DF.Currency
		base_taxes_and_charges_deducted: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		billing_address: DF.Link | None
		billing_address_display: DF.TextEditor | None
		buying_price_list: DF.Link | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.SmallText | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link
		customer: DF.Link | None
		customer_contact_display: DF.SmallText | None
		customer_contact_email: DF.Code | None
		customer_contact_mobile: DF.SmallText | None
		customer_contact_person: DF.Link | None
		customer_name: DF.Data | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.Link | None
		dispatch_address_display: DF.TextEditor | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		has_unit_price_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		inter_company_order_reference: DF.Link | None
		is_internal_supplier: DF.Check
		is_subcontracted: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[PurchaseOrderItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		mps: DF.Link | None
		named_place: DF.Data | None
		naming_series: DF.Literal["PUR-ORD-.YYYY.-"]
		net_total: DF.Currency
		order_confirmation_date: DF.Date | None
		order_confirmation_no: DF.Data | None
		other_charges_calculation: DF.TextEditor | None
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		per_billed: DF.Percent
		per_received: DF.Percent
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link | None
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		ref_sq: DF.Link | None
		represents_company: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		scan_barcode: DF.Data | None
		schedule_date: DF.Date | None
		select_print_heading: DF.Link | None
		set_from_warehouse: DF.Link | None
		set_reserve_warehouse: DF.Link | None
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"On Hold",
			"To Receive and Bill",
			"To Bill",
			"To Receive",
			"Completed",
			"Cancelled",
			"Closed",
			"Delivered",
		]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_group: DF.Link | None
		supplier_name: DF.Data | None
		supplier_warehouse: DF.Link | None
		tax_category: DF.Link | None
		taxes: DF.Table[PurchaseTaxesandCharges]
		taxes_and_charges: DF.Link | None
		taxes_and_charges_added: DF.Currency
		taxes_and_charges_deducted: DF.Currency
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		title: DF.Data | None
		to_date: DF.Date | None
		total: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transaction_date: DF.Date
		transaction_time: DF.Time | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Material Request Item",
				"join_field": "material_request_item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Material Request",
				"target_parent_field": "per_ordered",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
				"percent_join_field": "material_request",
				"global_allowance_field": "over_order_allowance",
				"global_allowance_doctype": "Buying Settings",
				"item_allowance_field": "over_order_allowance",
			}
		]

	def onload(self):
		self.set_onload("can_update_items", self.can_update_items())
		self.set_onload("has_pending_receivable_qty", self.has_pending_receivable_qty())

	def before_validate(self):
		self.set_has_unit_price_items()
		self.flags.allow_zero_qty = self.has_unit_price_items

		if self.is_subcontracted:
			self.status_updater[0]["source_field"] = "fg_item_qty"

	def validate(self):
		super().validate()

		self.set_status()

		self.validate_supplier()
		self.validate_schedule_date()
		validate_for_items(self)
		self.check_for_on_hold_or_closed_status("Material Request", "material_request")

		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")

		self.validate_with_previous_doc()
		self.validate_minimum_order_qty()
		validate_against_blanket_order(self)

		SubcontractingService(self).validate_fg_item_for_subcontracting()

		if not self.advance_payment_status:
			self.advance_payment_status = "Not Initiated"

		validate_inter_company_party(
			self.doctype, self.supplier, self.company, self.inter_company_order_reference
		)
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def set_has_unit_price_items(self):
		"""
		If permitted in settings and any item has 0 qty, the PO has unit price items.
		"""
		if not frappe.db.get_single_value("Buying Settings", "allow_zero_qty_in_purchase_order"):
			return

		self.has_unit_price_items = any(
			not row.qty for row in self.get("items") if (row.item_code and not row.qty)
		)

	def validate_with_previous_doc(self):
		mri_compare_fields = [["project", "="], ["item_code", "="]]
		if self.is_subcontracted:
			mri_compare_fields = [["project", "="]]

		super().validate_with_previous_doc(
			{
				"Supplier Quotation": {
					"ref_dn_field": "supplier_quotation",
					"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
				},
				"Supplier Quotation Item": {
					"ref_dn_field": "supplier_quotation_item",
					"compare_fields": [
						["project", "="],
						["item_code", "="],
						["uom", "="],
						["conversion_factor", "="],
					],
					"is_child_table": True,
				},
				"Material Request": {
					"ref_dn_field": "material_request",
					"compare_fields": [["company", "="]],
				},
				"Material Request Item": {
					"ref_dn_field": "material_request_item",
					"compare_fields": mri_compare_fields,
					"is_child_table": True,
				},
			}
		)

		if cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate")):
			self.validate_rate_with_reference_doc(
				[["Supplier Quotation", "supplier_quotation", "supplier_quotation_item"]]
			)

	def validate_supplier(self):
		prevent_po = frappe.db.get_value("Supplier", self.supplier, "prevent_pos")
		if prevent_po:
			standing = frappe.db.get_value("Supplier Scorecard", self.supplier, "status")
			if standing:
				frappe.throw(
					_("Purchase Orders are not allowed for {0} due to a scorecard standing of {1}.").format(
						self.supplier, standing
					)
				)

		warn_po = frappe.db.get_value("Supplier", self.supplier, "warn_pos")
		if warn_po:
			standing = frappe.db.get_value("Supplier Scorecard", self.supplier, "status")
			frappe.msgprint(
				_(
					"{0} currently has a {1} Supplier Scorecard standing, and Purchase Orders to this supplier should be issued with caution."
				).format(self.supplier, standing),
				title=_("Caution"),
				indicator="orange",
			)

		self.party_account_currency = get_party_account_currency("Supplier", self.supplier, self.company)

	def validate_minimum_order_qty(self):
		"""Check if total ordered quantities meet the Item's minimum order requirement."""
		if not self.get("items"):
			return
		items = list(set(d.item_code for d in self.get("items")))

		itemwise_min_order_qty = frappe._dict(
			frappe.get_all(
				"Item", fields=["name", "min_order_qty"], filters={"name": ["in", items]}, as_list=True
			)
		)

		itemwise_qty = frappe._dict()
		for d in self.get("items"):
			itemwise_qty.setdefault(d.item_code, 0)
			itemwise_qty[d.item_code] += flt(d.stock_qty)

		for item_code, qty in itemwise_qty.items():
			if flt(qty) < flt(itemwise_min_order_qty.get(item_code)):
				frappe.throw(
					_(
						"Item {0}: Ordered qty {1} cannot be less than minimum order qty {2} (defined in Item)."
					).format(item_code, qty, itemwise_min_order_qty.get(item_code))
				)

	def get_schedule_dates(self):
		for d in self.get("items"):
			if d.material_request_item and not d.schedule_date:
				d.schedule_date = frappe.db.get_value(
					"Material Request Item", d.material_request_item, "schedule_date"
				)

	@frappe.whitelist()
	def get_last_purchase_rate(self):
		"""get last purchase rates for all items"""

		conversion_rate = flt(self.get("conversion_rate")) or 1.0
		for d in self.get("items"):
			if d.item_code:
				last_purchase_details = get_last_purchase_details(d.item_code, self.name)
				if last_purchase_details:
					d.base_price_list_rate = last_purchase_details["base_price_list_rate"] * (
						flt(d.conversion_factor) or 1.0
					)
					d.discount_percentage = last_purchase_details["discount_percentage"]
					d.base_rate = last_purchase_details["base_rate"] * (flt(d.conversion_factor) or 1.0)
					d.price_list_rate = d.base_price_list_rate / conversion_rate
					d.rate = d.base_rate / conversion_rate
					d.last_purchase_rate = d.rate
				else:
					item_last_purchase_rate = frappe.get_cached_value(
						"Item", d.item_code, "last_purchase_rate"
					)
					if item_last_purchase_rate:
						d.base_price_list_rate = (
							d.base_rate
						) = d.price_list_rate = d.rate = d.last_purchase_rate = item_last_purchase_rate

	def update_ordered_qty(self, po_item_rows=None):
		"""update requested qty (before ordered_qty is updated)"""
		item_wh_list = []
		for d in self.get("items"):
			if (
				(not po_item_rows or d.name in po_item_rows)
				and [d.item_code, d.warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", d.item_code, "is_stock_item")
				and d.warehouse
				and not d.delivered_by_supplier
			):
				item_wh_list.append([d.item_code, d.warehouse])
		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"ordered_qty": get_ordered_qty(item_code, warehouse)})

	def update_status(self, status):
		StatusService(self).update_status(status)

	def on_submit(self):
		super().on_submit()

		if self.is_against_so():
			self.update_status_updater()

		if self.is_against_pp():
			self.update_status_updater_if_from_pp()

		self.update_prevdoc_status()
		if not self.is_subcontracted:
			self.update_requested_qty()

		self.update_ordered_qty()
		self.validate_budget()

		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		self.update_blanket_order()

		update_linked_doc(self.doctype, self.name, self.inter_company_order_reference)

		SubcontractingService(self).auto_create_subcontracting_order()

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Payment Ledger Entry",
			"Advance Payment Ledger Entry",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
		)

		super().on_cancel()

		if self.is_against_so():
			self.update_status_updater()

		if self.is_against_pp():
			self.update_status_updater_if_from_pp()

		drop_ship_service = DropShipService(self)
		if drop_ship_service.has_drop_ship_item():
			drop_ship_service.set_received_qty_to_zero_for_drop_ship_items()
			self.update_receiving_percentage()

		self.check_for_on_hold_or_closed_status("Material Request", "material_request")

		self.db_set("status", "Cancelled")

		self.update_prevdoc_status()

		# Must be called after updating ordered qty in Material Request
		# bin uses Material Request Items to recalculate & update
		if not self.is_subcontracted:
			self.update_requested_qty()

		self.update_ordered_qty()

		self.update_blanket_order()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_order_reference)

	def update_status_updater(self):
		self.status_updater.append(
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Sales Order Item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "",
				"join_field": "sales_order_item",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
			}
		)
		self.status_updater.append(
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Packed Item",
				"target_field": "ordered_qty",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "",
				"join_field": "sales_order_packed_item",
				"target_ref_field": "qty",
				"source_field": "stock_qty",
			}
		)

	def update_status_updater_if_from_pp(self):
		self.status_updater.append(
			{
				"source_dt": "Purchase Order Item",
				"target_dt": "Production Plan Sub Assembly Item",
				"join_field": "production_plan_sub_assembly_item",
				"target_field": "received_qty",
				"target_parent_dt": "Production Plan",
				"target_parent_field": "",
				"target_ref_field": "qty",
				"source_field": "fg_item_qty",
			}
		)

	@frappe.whitelist()
	def update_dropship_received_qty(self, data: list[dict]):
		DropShipService(self).update_dropship_received_qty(data)

	def is_against_so(self):
		return any(d.sales_order for d in self.items if d.sales_order)

	def is_against_pp(self):
		return any(d.production_plan for d in self.items if d.production_plan)

	def update_receiving_percentage(self):
		StatusService(self).update_receiving_percentage()

	def set_service_items_for_finished_goods(self):
		SubcontractingService(self).set_service_items_for_finished_goods()

	def can_update_items(self) -> bool:
		return SubcontractingService(self).can_update_items()

	def has_pending_receivable_qty(self) -> bool:
		"""Return True if any non-drop-ship item can still be received,
		considering the configured over_delivery_receipt_allowance.
		"""
		for item in self.get("items", []):
			if item.delivered_by_supplier:
				continue
			tolerance = flt(get_allowance_for(item.item_code, qty_or_amount="qty")[0])
			max_receivable_qty = flt(item.qty) * (100 + tolerance) / 100
			if abs(flt(item.received_qty)) < abs(max_receivable_qty):
				return True
		return False

	def update_ordered_qty_in_so_for_removed_items(self, removed_items):
		"""
		Updates ordered_qty in linked SO when item rows are removed using Update Items
		"""
		if not self.is_against_so():
			return
		for item in removed_items:
			sales_order_item = item.get("sales_order_item")
			if not sales_order_item:
				continue

			prev_ordered_qty = flt(
				frappe.get_cached_value("Sales Order Item", sales_order_item, "ordered_qty")
			)
			# `Sales Order Item.ordered_qty` is tracked in stock UOM (see status_updater);
			# use the row's stock_qty so PO UOMs that differ from stock UOM decrement correctly.
			qty_in_stock_uom = flt(item.get("stock_qty")) or flt(item.qty) * flt(
				item.get("conversion_factor") or 1
			)

			frappe.db.set_value(
				"Sales Order Item", sales_order_item, "ordered_qty", prev_ordered_qty - qty_in_stock_uom
			)


@frappe.request_cache
def item_last_purchase_rate(name, conversion_rate, item_code, conversion_factor=1.0):
	"""get last purchase rate for an item"""

	conversion_rate = flt(conversion_rate) or 1.0

	last_purchase_details = get_last_purchase_details(item_code, name)
	if last_purchase_details:
		last_purchase_rate = (
			last_purchase_details["base_net_rate"] * (flt(conversion_factor) or 1.0)
		) / conversion_rate
		return last_purchase_rate
	else:
		item_last_purchase_rate = frappe.get_cached_value("Item", item_code, "last_purchase_rate")
		if item_last_purchase_rate:
			return item_last_purchase_rate


@frappe.whitelist()
def close_or_unclose_purchase_orders(names: str, status: str):
	if not frappe.has_permission("Purchase Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	names = json.loads(names)
	for name in names:
		po = frappe.get_lazy_doc("Purchase Order", name)
		if po.docstatus == 1:
			if status == "Closed":
				if po.status not in ("Cancelled", "Closed") and (
					po.per_received < 100 or po.per_billed < 100
				):
					po.update_status(status)
			else:
				if po.status == "Closed":
					po.update_status("Draft")
			po.update_blanket_order()

	frappe.local.message_log = []


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Purchase Orders"),
			"list_template": "templates/includes/list/list.html",
		}
	)
	return list_context


@frappe.whitelist()
def update_status(status: str, name: str):
	po = frappe.get_lazy_doc("Purchase Order", name, check_permission="submit")
	po.update_status(status)
	DropShipService(po).update_delivered_qty_in_sales_order()
