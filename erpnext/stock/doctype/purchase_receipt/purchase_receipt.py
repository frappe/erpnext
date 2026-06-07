# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate

import erpnext
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from erpnext.controllers.buying_controller import BuyingController
from erpnext.stock.doctype.purchase_receipt.services.billing_status import BillingStatusService
from erpnext.stock.doctype.purchase_receipt.services.provisional_accounting import (
	ProvisionalAccountingService,
)
from erpnext.stock.doctype.purchase_receipt.services.stock_reservation import StockReservationService

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class PurchaseReceipt(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import (
			PurchaseTaxesandCharges,
		)
		from erpnext.buying.doctype.purchase_receipt_item_supplied.purchase_receipt_item_supplied import (
			PurchaseReceiptItemSupplied,
		)
		from erpnext.stock.doctype.purchase_receipt_item.purchase_receipt_item import PurchaseReceiptItem

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		apply_putaway_rule: DF.Check
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
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.Link | None
		dispatch_address_display: DF.TextEditor | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		instructions: DF.SmallText | None
		inter_company_reference: DF.Link | None
		is_internal_supplier: DF.Check
		is_return: DF.Check
		is_subcontracted: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[PurchaseReceiptItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		lr_date: DF.Date | None
		lr_no: DF.Data | None
		named_place: DF.Data | None
		naming_series: DF.Literal["MAT-PRE-.YYYY.-", "MAT-PR-RET-.YYYY.-"]
		net_total: DF.Currency
		other_charges_calculation: DF.TextEditor | None
		per_billed: DF.Percent
		per_returned: DF.Percent
		plc_conversion_rate: DF.Float
		posting_date: DF.Date
		posting_time: DF.Time
		price_list_currency: DF.Link | None
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		range: DF.Data | None
		rejected_warehouse: DF.Link | None
		remarks: DF.SmallText | None
		represents_company: DF.Link | None
		return_against: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		set_from_warehouse: DF.Link | None
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Partly Billed",
			"To Bill",
			"Completed",
			"Return",
			"Return Issued",
			"Cancelled",
			"Closed",
		]
		subcontracting_receipt: DF.Link | None
		supplied_items: DF.Table[PurchaseReceiptItemSupplied]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_delivery_note: DF.Data | None
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
		total: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		transporter_name: DF.Data | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"target_dt": "Purchase Order Item",
				"join_field": "purchase_order_item",
				"target_field": "received_qty",
				"target_parent_dt": "Purchase Order",
				"target_parent_field": "per_received",
				"target_ref_field": "qty",
				"source_dt": "Purchase Receipt Item",
				"source_field": "received_qty",
				"second_source_dt": "Purchase Invoice Item",
				"second_source_field": "received_qty",
				"second_join_field": "po_detail",
				"percent_join_field": "purchase_order",
				"overflow_type": "receipt",
				"second_source_extra_cond": """ and exists(select name from `tabPurchase Invoice`
				where name=`tabPurchase Invoice Item`.parent and update_stock = 1)""",
			},
			{
				"source_dt": "Purchase Receipt Item",
				"target_dt": "Material Request Item",
				"join_field": "material_request_item",
				"target_field": "received_qty",
				"target_parent_dt": "Material Request",
				"target_parent_field": "per_received",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
				"percent_join_field": "material_request",
				"validate_qty": False,
			},
			{
				"source_dt": "Purchase Receipt Item",
				"target_dt": "Purchase Invoice Item",
				"join_field": "purchase_invoice_item",
				"target_field": "received_qty",
				"target_parent_dt": "Purchase Invoice",
				"target_parent_field": "per_received",
				"target_ref_field": "qty",
				"source_field": "received_qty",
				"percent_join_field": "purchase_invoice",
				"overflow_type": "receipt",
			},
			{
				"source_dt": "Purchase Receipt Item",
				"target_dt": "Delivery Note Item",
				"join_field": "delivery_note_item",
				"source_field": "received_qty",
				"target_field": "received_qty",
				"target_parent_dt": "Delivery Note",
				"target_ref_field": "qty",
				"overflow_type": "receipt",
			},
		]

		if cint(self.is_return):
			self.status_updater.extend(
				[
					{
						"source_dt": "Purchase Receipt Item",
						"target_dt": "Purchase Order Item",
						"join_field": "purchase_order_item",
						"target_field": "returned_qty",
						"source_field": "-1 * qty",
						"second_source_dt": "Purchase Invoice Item",
						"second_source_field": "-1 * qty",
						"second_join_field": "po_detail",
						"extra_cond": """ and exists (select name from `tabPurchase Receipt`
						where name=`tabPurchase Receipt Item`.parent and is_return=1)""",
						"second_source_extra_cond": """ and exists (select name from `tabPurchase Invoice`
						where name=`tabPurchase Invoice Item`.parent and is_return=1 and update_stock=1)""",
					},
					{
						"source_dt": "Purchase Receipt Item",
						"target_dt": "Purchase Receipt Item",
						"join_field": "purchase_receipt_item",
						"target_field": "returned_qty",
						"target_parent_dt": "Purchase Receipt",
						"target_parent_field": "per_returned",
						"target_ref_field": "received_stock_qty",
						"source_field": "-1 * received_stock_qty",
						"percent_join_field_parent": "return_against",
					},
				]
			)

	def before_validate(self):
		from erpnext.stock.doctype.putaway_rule.putaway_rule import apply_putaway_rule

		if self.get("items") and self.apply_putaway_rule and not self.get("is_return"):
			if items := apply_putaway_rule(self.doctype, self.get("items"), self.company):
				self.items = items

	def validate(self):
		self.validate_posting_time()
		self.validate_posting_date_with_po()
		super().validate()

		if self._action != "submit":
			self.set_status()

		self.po_required()
		self.validate_items_quality_inspection()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer()
		self.validate_cwip_accounts()
		ProvisionalAccountingService(self).validate_provisional_expense_account()

		self.check_for_on_hold_or_closed_status("Purchase Order", "purchase_order")

		if getdate(self.posting_date) > getdate(nowdate()):
			throw(_("Posting Date cannot be future date"))

		self.get_current_stock()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")

	def validate_uom_is_integer(self):
		super().validate_uom_is_integer("uom", ["qty", "received_qty"], "Purchase Receipt Item")
		super().validate_uom_is_integer("stock_uom", "stock_qty", "Purchase Receipt Item")

	def validate_cwip_accounts(self):
		for item in self.get("items"):
			if item.is_fixed_asset and is_cwip_accounting_enabled(item.asset_category):
				# check cwip accounts before making auto assets
				# Improves UX by not giving messages of "Assets Created" before throwing error of not finding arbnb account
				self.get_company_default("asset_received_but_not_billed")
				get_asset_account(
					"capital_work_in_progress_account",
					asset_category=item.asset_category,
					company=self.company,
				)
				break

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Purchase Order": {
					"ref_dn_field": "purchase_order",
					"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
				},
				"Purchase Order Item": {
					"ref_dn_field": "purchase_order_item",
					"compare_fields": [["project", "="], ["uom", "="], ["item_code", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if (
			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[["Purchase Order", "purchase_order", "purchase_order_item"]]
			)

	def po_required(self):
		if (
			frappe.db.get_single_value("Buying Settings", "po_required") == "Yes"
			and not self.is_internal_transfer()
		):
			for d in self.get("items"):
				if not d.purchase_order:
					frappe.throw(_("Purchase Order number required for Item {0}").format(d.item_code))

	def validate_items_quality_inspection(self):
		for item in self.get("items"):
			if item.quality_inspection:
				qi = frappe.db.get_value(
					"Quality Inspection",
					item.quality_inspection,
					["reference_type", "reference_name", "item_code"],
					as_dict=True,
				)

				if qi.reference_type != self.doctype or qi.reference_name != self.name:
					msg = f"""Row #{item.idx}: Please select a valid Quality Inspection with Reference Type
						{frappe.bold(self.doctype)} and Reference Name {frappe.bold(self.name)}."""
					frappe.throw(_(msg))

				if qi.item_code != item.item_code:
					msg = f"""Row #{item.idx}: Please select a valid Quality Inspection with Item Code
						{frappe.bold(item.item_code)}."""
					frappe.throw(_(msg))

	def get_already_received_qty(self, po, po_detail):
		qty = frappe.db.sql(
			"""select sum(qty) from `tabPurchase Receipt Item`
			where purchase_order_item = %s and docstatus = 1
			and purchase_order=%s
			and parent != %s""",
			(po_detail, po, self.name),
		)
		return qty and flt(qty[0][0]) or 0.0

	def get_po_qty_and_warehouse(self, po_detail):
		po_qty, po_warehouse = frappe.db.get_value("Purchase Order Item", po_detail, ["qty", "warehouse"])
		return po_qty, po_warehouse

	# on submit
	def on_submit(self):
		super().on_submit()

		# Check for Approving Authority
		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		self.update_prevdoc_status()
		if flt(self.per_billed) < 100:
			self.update_billing_status()
		else:
			self.db_set("status", "Completed")

		self.make_bundle_for_sales_purchase_return()
		self.make_bundle_using_old_serial_batch_fields()
		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty, reserved_qty_for_subcontract in bin
		# depends upon updated ordered qty in PO
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.set_consumed_qty_in_subcontract_order()
		StockReservationService(self).reserve_stock()
		self.update_received_qty_if_from_pp()

	def update_received_qty_if_from_pp(self):
		from frappe.query_builder.functions import Coalesce, Sum

		items_from_po = [item.purchase_order_item for item in self.items if item.purchase_order_item]
		if items_from_po:
			table = frappe.qb.DocType("Purchase Order Item")
			subquery = (
				frappe.qb.from_(table)
				.select(table.production_plan_sub_assembly_item)
				.distinct()
				.where(
					table.name.isin(items_from_po)
					& Coalesce(table.production_plan_sub_assembly_item, "").ne("")
				)
			)
			result = subquery.run(as_dict=True)
			if result:
				result = [item.production_plan_sub_assembly_item for item in result]
				query = (
					frappe.qb.from_(table)
					.select(
						table.production_plan_sub_assembly_item,
						Sum(table.received_qty / (table.qty / table.fg_item_qty)).as_("received_qty"),
					)
					.where(table.production_plan_sub_assembly_item.isin(result))
					.groupby(table.production_plan_sub_assembly_item)
				)
				for row in query.run(as_dict=True):
					frappe.set_value(
						"Production Plan Sub Assembly Item",
						row.production_plan_sub_assembly_item,
						"received_qty",
						row.received_qty,
					)

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql(
			"""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			(self.name),
		)
		if submit_rv:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(self.submit_rv[0][0]))

	def on_cancel(self):
		super().on_cancel()

		self.check_for_on_hold_or_closed_status("Purchase Order", "purchase_order")
		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = frappe.db.sql(
			"""select t1.name
			from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2
			where t1.name = t2.parent and t2.purchase_receipt = %s and t1.docstatus = 1""",
			self.name,
		)
		if submitted:
			frappe.throw(_("Purchase Invoice {0} is already submitted").format(submitted[0][0]))

		self.update_prevdoc_status()
		self.update_billing_status()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Serial and Batch Bundle",
		)
		self.delete_auto_created_batches()
		self.set_consumed_qty_in_subcontract_order()
		self.update_received_qty_if_from_pp()

	def before_cancel(self):
		super().before_cancel()
		self.remove_amount_difference_with_purchase_invoice()

	def remove_amount_difference_with_purchase_invoice(self):
		for item in self.items:
			item.amount_difference_with_purchase_invoice = 0

	def get_gl_entries(self, inventory_account_map=None, via_landed_cost_voucher=False):
		from erpnext.stock.doctype.purchase_receipt.services.gl_composer import (
			PurchaseReceiptGLComposer,
		)

		return PurchaseReceiptGLComposer(self).compose(inventory_account_map, via_landed_cost_voucher)

	def add_provisional_gl_entry(
		self, item, gl_entries, posting_date, provisional_account, reverse=0, item_amount=None
	):
		ProvisionalAccountingService(self).add_provisional_gl_entry(
			item, gl_entries, posting_date, provisional_account, reverse, item_amount
		)

	def is_landed_cost_booked_for_any_item(self) -> bool:
		for x in self.items:
			if x.landed_cost_voucher_amount != 0:
				return True

		return False

	def update_assets(self, item, valuation_rate):
		assets = frappe.db.get_all(
			"Asset",
			filters={
				"purchase_receipt": self.name,
				"item_code": item.item_code,
				"purchase_receipt_item": ("in", [item.name, ""]),
			},
			fields=["name", "asset_quantity"],
		)

		for asset in assets:
			purchase_amount = flt(valuation_rate) * asset.asset_quantity
			frappe.db.set_value(
				"Asset",
				asset.name,
				{
					"net_purchase_amount": purchase_amount,
					"purchase_amount": purchase_amount,
				},
			)

	def update_status(self, status):
		self.set_status(update=True, status=status)
		self.notify_update()
		clear_doctype_notifications(self)

	def update_billing_status(self, update_modified=True):
		BillingStatusService(self).update_billing_status(update_modified)

	def enable_recalculate_rate_in_sles(self):
		rejected_warehouses = frappe.get_all(
			"Purchase Receipt Item", filters={"parent": self.name}, pluck="rejected_warehouse"
		)

		sle_table = frappe.qb.DocType("Stock Ledger Entry")
		(
			frappe.qb.update(sle_table)
			.set(sle_table.recalculate_rate, 1)
			.where(sle_table.voucher_no == self.name)
			.where(sle_table.voucher_type == "Purchase Receipt")
			.where(sle_table.warehouse.notin(rejected_warehouses))
		).run()


def get_stock_value_difference(voucher_no, voucher_detail_no, warehouse):
	return frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"voucher_type": "Purchase Receipt",
			"voucher_no": voucher_no,
			"voucher_detail_no": voucher_detail_no,
			"warehouse": warehouse,
			"is_cancelled": 0,
		},
		"stock_value_difference",
	)


@frappe.whitelist()
def update_purchase_receipt_status(docname: str, status: str):
	pr = frappe.get_lazy_doc("Purchase Receipt", docname, check_permission="submit")
	pr.update_status(status)


@erpnext.allow_regional
def update_regional_gl_entries(gl_list, doc):
	return


@frappe.whitelist()
def make_lcv(doctype: str, docname: str):
	landed_cost_voucher = frappe.new_doc("Landed Cost Voucher")

	details = frappe.db.get_value(doctype, docname, ["supplier", "company", "base_grand_total"], as_dict=1)

	landed_cost_voucher.company = details.company

	landed_cost_voucher.append(
		"purchase_receipts",
		{
			"receipt_document_type": doctype,
			"receipt_document": docname,
			"grand_total": details.base_grand_total,
			"supplier": details.supplier,
		},
	)

	landed_cost_voucher.get_items_from_purchase_receipts()

	return landed_cost_voucher.as_dict()
