# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.document import Document
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, flt, get_datetime, getdate, nowdate
from pypika import functions as fn

import erpnext
from erpnext.accounts.utils import get_account_currency
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from erpnext.controllers.buying_controller import BuyingController
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation

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
		self.validate_provisional_expense_account()

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

	def validate_provisional_expense_account(self):
		provisional_accounting_for_non_stock_items = cint(
			frappe.db.get_value("Company", self.company, "enable_provisional_accounting_for_non_stock_items")
		)

		if not provisional_accounting_for_non_stock_items:
			return

		default_provisional_account = self.get_company_default("default_provisional_account")
		for item in self.get("items"):
			if not item.get("provisional_expense_account"):
				item.provisional_expense_account = default_provisional_account

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
		self.reserve_stock()
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
		credit_currency = get_account_currency(provisional_account)
		expense_account = item.expense_account
		debit_currency = get_account_currency(item.expense_account)
		remarks = self.get("remarks") or _("Accounting Entry for Service")
		multiplication_factor = 1
		amount = item.base_amount

		if reverse:
			multiplication_factor = -1
			# Post reverse entry for previously posted amount
			amount = item_amount
			expense_account = frappe.db.get_value(
				"Purchase Receipt Item", {"name": item.get("pr_detail")}, ["expense_account"]
			)

		self.add_gl_entry(
			gl_entries=gl_entries,
			account=provisional_account,
			cost_center=item.cost_center,
			debit=0.0,
			credit=multiplication_factor * amount,
			remarks=remarks,
			against_account=expense_account,
			account_currency=credit_currency,
			project=item.project,
			voucher_detail_no=item.name,
			item=item,
			posting_date=posting_date,
		)

		self.add_gl_entry(
			gl_entries=gl_entries,
			account=expense_account,
			cost_center=item.cost_center,
			debit=multiplication_factor * amount,
			credit=0.0,
			remarks=remarks,
			against_account=provisional_account,
			account_currency=debit_currency,
			project=item.project,
			voucher_detail_no=item.name,
			item=item,
			posting_date=posting_date,
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
		updated_pr = [self.name]
		po_details = []
		for d in self.get("items"):
			if d.get("purchase_invoice") and d.get("purchase_invoice_item"):
				d.db_set("billed_amt", d.amount, update_modified=update_modified)
			elif d.purchase_order_item:
				po_details.append(d.purchase_order_item)

		if po_details:
			updated_pr += update_billed_amount_based_on_po(po_details, update_modified, self)

		for pr in set(updated_pr):
			pr_doc = self if (pr == self.name) else frappe.get_lazy_doc("Purchase Receipt", pr)
			update_billing_percentage(pr_doc, update_modified=update_modified)

	def reserve_stock(self):
		self.reserve_stock_for_sales_order()
		self.reserve_stock_for_production_plan()

	def reserve_stock_for_sales_order(self):
		if (
			self.is_return
			or not frappe.get_single_value("Stock Settings", "enable_stock_reservation")
			or not frappe.get_single_value("Stock Settings", "auto_reserve_stock_for_sales_order_on_purchase")
		):
			return

		self.reload()  # reload to get the Serial and Batch Bundle Details

		so_items_details_map = {}
		for item in self.items:
			if item.sales_order and item.sales_order_item:
				item_details = {
					"sales_order_item": item.sales_order_item,
					"item_code": item.item_code,
					"warehouse": item.warehouse,
					"qty_to_reserve": item.stock_qty,
					"from_voucher_no": item.parent,
					"from_voucher_detail_no": item.name,
					"serial_and_batch_bundle": item.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(item.sales_order, []).append(item_details)

		if so_items_details_map:
			if get_datetime(f"{self.posting_date} {self.posting_time}") > get_datetime():
				return frappe.msgprint(
					_("Cannot create Stock Reservation Entries for future dated Purchase Receipts.")
				)

			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_lazy_doc("Sales Order", so)
				so_doc.create_stock_reservation_entries(
					items_details=items_details,
					from_voucher_type="Purchase Receipt",
					notify=True,
				)

	def reserve_stock_for_production_plan(self):
		if self.is_return or not frappe.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		production_plan_references = self.get_production_plan_references()
		production_plan_items = []
		self.reload()

		docnames = []
		for row in self.items:
			if row.material_request_item and row.material_request_item in production_plan_references:
				_ref = production_plan_references[row.material_request_item]
				docnames.append(_ref.production_plan)
				row.update(
					{
						"voucher_type": "Production Plan",
						"voucher_no": _ref.production_plan,
						"voucher_detail_no": _ref.material_request_plan_item,
						"from_voucher_no": self.name,
						"from_voucher_detail_no": row.name,
						"from_voucher_type": self.doctype,
						"serial_and_batch_bundles": [row.serial_and_batch_bundle],
					}
				)

				production_plan_items.append(row)

		if not production_plan_items:
			return

		sre = StockReservation(doc=self, items=production_plan_items)
		sre.make_stock_reservation_entries()
		if docnames:
			sre.transfer_reservation_entries_to(
				docnames, from_doctype="Production Plan", to_doctype="Work Order"
			)

	def get_production_plan_references(self):
		production_plan_references = frappe._dict()
		material_request_items = []

		for row in self.items:
			if row.material_request_item:
				material_request_items.append(row.material_request_item)

		if not material_request_items:
			return frappe._dict()

		items = frappe.get_all(
			"Material Request Item",
			fields=["material_request_plan_item", "production_plan", "name"],
			filters={"name": ["in", material_request_items], "docstatus": 1},
		)

		for item in items:
			if not item.production_plan:
				continue

			production_plan_references.setdefault(item.name, item)

		return production_plan_references

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


def update_billed_amount_based_on_po(po_details, update_modified=True, pr_doc=None):
	po_billed_amt_details = get_billed_amount_against_po(po_details)

	# Get all Purchase Receipt Item rows against the Purchase Order Items
	pr_details = get_purchase_receipts_against_po_details(po_details)

	pr_items = [pr_detail.name for pr_detail in pr_details]
	pr_items_billed_amount = get_billed_amount_against_pr(pr_items)

	updated_pr = []
	for pr_item in pr_details:
		billed_amt_against_po, billed_qty_against_po = 0, 0
		if billed_details := po_billed_amt_details.get(pr_item.purchase_order_item):
			billed_amt_against_po = flt(billed_details["billed_amt"])
			billed_qty_against_po = flt(billed_details["billed_qty"])

		# Get billed amount directly against Purchase Receipt
		billed_amt_against_pr = flt(pr_items_billed_amount.get(pr_item.name, 0))

		# Distribute billed amount directly against PO between PRs based on FIFO
		if billed_amt_against_po and billed_amt_against_pr < pr_item.amount:
			if not billed_amt_against_pr and billed_qty_against_po and billed_qty_against_po > pr_item.qty:
				billed_amt_against_pr = flt(flt(billed_amt_against_po) * flt(pr_item.qty)) / flt(
					billed_qty_against_po
				)
			else:
				pending_to_bill = flt(pr_item.amount) - billed_amt_against_pr
				if pending_to_bill <= billed_amt_against_po:
					billed_amt_against_pr += pending_to_bill
					billed_amt_against_po -= pending_to_bill
				else:
					billed_amt_against_pr += billed_amt_against_po
					billed_amt_against_po = 0

				po_billed_amt_details[pr_item.purchase_order_item]["billed_amt"] = billed_amt_against_po

		if pr_item.billed_amt != billed_amt_against_pr:
			# update existing doc if possible
			if pr_doc and pr_item.parent == pr_doc.name:
				pr_item = next((item for item in pr_doc.items if item.name == pr_item.name), None)
				pr_item.db_set("billed_amt", billed_amt_against_pr, update_modified=update_modified)

			else:
				frappe.db.set_value(
					"Purchase Receipt Item",
					pr_item.name,
					"billed_amt",
					billed_amt_against_pr,
					update_modified=update_modified,
				)

			updated_pr.append(pr_item.parent)

	return updated_pr


def get_purchase_receipts_against_po_details(po_details):
	# Get Purchase Receipts against Purchase Order Items

	purchase_receipt = frappe.qb.DocType("Purchase Receipt")
	purchase_receipt_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(purchase_receipt)
		.inner_join(purchase_receipt_item)
		.on(purchase_receipt.name == purchase_receipt_item.parent)
		.select(
			purchase_receipt_item.name,
			purchase_receipt_item.qty,
			purchase_receipt_item.parent,
			purchase_receipt_item.amount,
			purchase_receipt_item.billed_amt,
			purchase_receipt_item.purchase_order_item,
		)
		.where(
			(purchase_receipt_item.purchase_order_item.isin(po_details))
			& (purchase_receipt.docstatus == 1)
			& (purchase_receipt.is_return == 0)
		)
		.orderby(CombineDatetime(purchase_receipt.posting_date, purchase_receipt.posting_time))
		.orderby(purchase_receipt.name)
	)

	return query.run(as_dict=True)


def get_billed_amount_against_pr(pr_items):
	# Get billed amount directly against Purchase Receipt

	if not pr_items:
		return {}

	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(purchase_invoice_item)
		.select(fn.Sum(purchase_invoice_item.amount).as_("billed_amt"), purchase_invoice_item.pr_detail)
		.where((purchase_invoice_item.pr_detail.isin(pr_items)) & (purchase_invoice_item.docstatus == 1))
		.groupby(purchase_invoice_item.pr_detail)
	).run(as_dict=1)

	return {d.pr_detail: flt(d.billed_amt) for d in query}


def get_billed_amount_against_po(po_items):
	# Get billed amount directly against Purchase Order
	if not po_items:
		return {}

	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(purchase_invoice_item)
		.inner_join(purchase_invoice)
		.on(purchase_invoice_item.parent == purchase_invoice.name)
		.select(
			fn.Sum(purchase_invoice_item.amount).as_("billed_amt"),
			fn.Sum(purchase_invoice_item.qty).as_("qty"),
			purchase_invoice_item.po_detail,
		)
		.where(
			(purchase_invoice_item.po_detail.isin(po_items))
			& (purchase_invoice.docstatus == 1)
			& (purchase_invoice_item.pr_detail.isnull())
			& (purchase_invoice.update_stock == 0)
		)
		.groupby(purchase_invoice_item.po_detail)
	).run(as_dict=1)

	return {d.po_detail: {"billed_amt": flt(d.billed_amt), "billed_qty": flt(d.qty)} for d in query}


def update_billing_percentage(pr_doc, update_modified=True, adjust_incoming_rate=False):
	# Update Billing % based on pending accepted qty
	buying_settings = frappe.get_single("Buying Settings")
	over_billing_allowance, role_allowed_to_over_bill = frappe.get_single_value(
		"Accounts Settings", ["over_billing_allowance", "role_allowed_to_over_bill"]
	)

	total_amount, total_billed_amount, pi_landed_cost_amount = 0, 0, 0
	item_wise_returned_qty = get_item_wise_returned_qty(pr_doc)
	billed_qty_amt = frappe._dict()

	if adjust_incoming_rate:
		billed_qty_amt = get_billed_qty_amount_against_purchase_receipt(pr_doc)
		billed_qty_amt_based_on_po = get_billed_qty_amount_against_purchase_order(pr_doc)

	for item in pr_doc.items:
		returned_qty = flt(item_wise_returned_qty.get(item.name))
		returned_amount = flt(returned_qty) * flt(item.rate)
		pending_amount = flt(item.amount) - returned_amount
		if buying_settings.bill_for_rejected_quantity_in_purchase_invoice:
			pending_amount = flt(item.amount)

		total_billable_amount = abs(flt(item.amount))
		if pending_amount > 0:
			total_billable_amount = pending_amount if item.billed_amt <= pending_amount else item.billed_amt

		total_amount += total_billable_amount
		total_billed_amount += abs(flt(item.billed_amt))

		if pr_doc.get("is_return") and not total_amount and total_billed_amount:
			total_amount = total_billed_amount

		amount = item.amount
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			amount += flt(item.rejected_qty * item.rate, item.precision("amount"))

		if adjust_incoming_rate:
			adjusted_amt = 0.0

			if (
				item.billed_amt is not None
				and item.amount is not None
				and (
					billed_qty_amt.get(item.name) or billed_qty_amt_based_on_po.get(item.purchase_order_item)
				)
			):
				qty = None
				if billed_qty_amt.get(item.name):
					qty = billed_qty_amt.get(item.name).get("qty")

				if not qty and billed_qty_amt_based_on_po.get(item.purchase_order_item):
					if item.qty < billed_qty_amt_based_on_po.get(item.purchase_order_item)["qty"]:
						qty = item.qty
					else:
						qty = billed_qty_amt_based_on_po.get(item.purchase_order_item)["qty"]

					billed_qty_amt_based_on_po[item.purchase_order_item]["qty"] -= qty

				billed_amt = item.billed_amt
				if billed_qty_amt.get(item.name):
					billed_amt = flt(billed_qty_amt.get(item.name).get("amount"))
				elif billed_qty_amt_based_on_po.get(item.purchase_order_item):
					total_billed_qty = (
						billed_qty_amt_based_on_po.get(item.purchase_order_item).get("qty") + qty
					)

					if total_billed_qty:
						billed_amt = flt(
							flt(billed_qty_amt_based_on_po.get(item.purchase_order_item).get("amount"))
							* (qty / total_billed_qty)
						)
					else:
						billed_amt = 0.0

					# Reduce billed amount based on PO for next iterations
					billed_qty_amt_based_on_po[item.purchase_order_item]["amount"] -= billed_amt

				if qty:
					adjusted_amt = (
						flt(billed_amt / qty) - (flt(item.rate) * flt(pr_doc.conversion_rate))
					) * item.qty

			adjusted_amt = flt(adjusted_amt, item.precision("amount"))
			pi_landed_cost_amount += adjusted_amt
			item.db_set("amount_difference_with_purchase_invoice", adjusted_amt, update_modified=False)
		elif amount and item.billed_amt > amount:
			per_over_billed = (flt(item.billed_amt / amount, 2) * 100) - 100
			if (
				per_over_billed > over_billing_allowance
				and role_allowed_to_over_bill not in frappe.get_roles()
			):
				frappe.throw(
					_("Over Billing Allowance exceeded for Purchase Receipt Item {0} ({1}) by {2}%").format(
						item.name, frappe.bold(item.item_code), per_over_billed - over_billing_allowance
					)
				)

	if pi_landed_cost_amount < 0:
		total_billed_amount += abs(pi_landed_cost_amount)

	percent_billed = round(100 * (total_billed_amount / (total_amount or 1)), 6)
	pr_doc.db_set("per_billed", percent_billed)

	if update_modified:
		pr_doc.set_status(update=True)
		pr_doc.notify_update()

	if adjust_incoming_rate:
		adjust_incoming_rate_for_pr(pr_doc)


def get_billed_qty_amount_against_purchase_receipt(pr_doc):
	pr_names = [d.name for d in pr_doc.items]
	parent_table = frappe.qb.DocType("Purchase Invoice")
	table = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(parent_table)
		.inner_join(table)
		.on(parent_table.name == table.parent)
		.select(
			table.pr_detail,
			fn.Sum(table.base_net_amount).as_("amount"),
			fn.Sum(table.qty).as_("qty"),
		)
		.where((table.pr_detail.isin(pr_names)) & (table.docstatus == 1))
		.groupby(table.pr_detail)
	)
	invoice_data = query.run(as_dict=1)

	if not invoice_data:
		return frappe._dict()

	billed_qty_amt = frappe._dict()

	for row in invoice_data:
		if row.pr_detail not in billed_qty_amt:
			billed_qty_amt[row.pr_detail] = {"amount": 0, "qty": 0}

		billed_qty_amt[row.pr_detail]["amount"] += flt(row.amount)
		billed_qty_amt[row.pr_detail]["qty"] += flt(row.qty)

	return billed_qty_amt


def get_billed_qty_amount_against_purchase_order(pr_doc):
	po_names = list(
		set(
			[
				d.purchase_order_item
				for d in pr_doc.items
				if d.purchase_order_item and not d.purchase_invoice_item
			]
		)
	)

	invoice_data_po_based = frappe._dict()
	if po_names:
		parent_table = frappe.qb.DocType("Purchase Invoice")
		table = frappe.qb.DocType("Purchase Invoice Item")

		query = (
			frappe.qb.from_(parent_table)
			.inner_join(table)
			.on(parent_table.name == table.parent)
			.select(
				table.po_detail,
				fn.Sum(table.qty).as_("qty"),
				fn.Sum(table.base_net_amount).as_("amount"),
			)
			.where((table.po_detail.isin(po_names)) & (table.docstatus == 1) & (table.pr_detail.isnull()))
			.groupby(table.po_detail)
		)

		invoice_data = query.run(as_dict=1)
		if not invoice_data:
			return frappe._dict()

		for row in invoice_data:
			if row.po_detail not in invoice_data_po_based:
				invoice_data_po_based[row.po_detail] = {"amount": 0, "qty": 0}

			invoice_data_po_based[row.po_detail]["amount"] += flt(row.amount)
			invoice_data_po_based[row.po_detail]["qty"] += flt(row.qty)

	return invoice_data_po_based


def adjust_incoming_rate_for_pr(doc):
	doc.update_valuation_rate(reset_outgoing_rate=False)

	for item in doc.get("items"):
		item.db_update()

	if doc.doctype == "Purchase Receipt":
		doc.enable_recalculate_rate_in_sles()

	doc.repost_future_sle_and_gle(force=True)


def get_item_wise_returned_qty(pr_doc):
	items = [d.name for d in pr_doc.items]

	return frappe._dict(
		frappe.get_all(
			"Purchase Receipt",
			fields=[
				"`tabPurchase Receipt Item`.purchase_receipt_item",
				{"SUM": [{"ABS": "`tabPurchase Receipt Item`.qty"}], "as": "qty"},
			],
			filters=[
				["Purchase Receipt", "docstatus", "=", 1],
				["Purchase Receipt", "is_return", "=", 1],
				["Purchase Receipt Item", "purchase_receipt_item", "in", items],
			],
			group_by="`tabPurchase Receipt Item`.purchase_receipt_item",
			as_list=1,
		)
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
