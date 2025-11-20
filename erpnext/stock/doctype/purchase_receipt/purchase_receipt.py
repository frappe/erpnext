# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, throw
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, flt, get_datetime, getdate, nowdate
from pypika import functions as fn

import erpnext
from erpnext.accounts.utils import get_account_currency
from erpnext.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.accounts_controller import merge_taxes
from erpnext.controllers.buying_controller import BuyingController
from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_transaction
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
		base_tax_withholding_net_total: DF.Currency
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
		is_old_subcontracting_flow: DF.Check
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
		tax_withholding_net_total: DF.Currency
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
			apply_putaway_rule(self.doctype, self.get("items"), self.company)

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

		self.check_on_hold_or_closed_status()

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
		if frappe.db.get_single_value("Buying Settings", "po_required") == "Yes":
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

	# Check for Closed status
	def check_on_hold_or_closed_status(self):
		check_list = []
		for d in self.get("items"):
			if d.meta.get_field("purchase_order") and d.purchase_order and d.purchase_order not in check_list:
				check_list.append(d.purchase_order)
				check_on_hold_or_closed_status("Purchase Order", d.purchase_order)

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
		from frappe.query_builder.functions import Sum

		items_from_po = [item.purchase_order_item for item in self.items if item.purchase_order_item]
		if items_from_po:
			table = frappe.qb.DocType("Purchase Order Item")
			subquery = (
				frappe.qb.from_(table)
				.select(table.production_plan_sub_assembly_item)
				.distinct()
				.where(table.name.isin(items_from_po) & table.production_plan_sub_assembly_item.isnotnull())
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

		self.check_on_hold_or_closed_status()
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
		from erpnext.accounts.general_ledger import process_gl_map

		gl_entries = []

		self.make_item_gl_entries(gl_entries, inventory_account_map=inventory_account_map)
		self.make_tax_gl_entries(gl_entries, via_landed_cost_voucher)
		self.set_gl_entry_for_purchase_expense(gl_entries)
		update_regional_gl_entries(gl_entries, self)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def make_item_gl_entries(self, gl_entries, inventory_account_map=None):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
			get_purchase_document_details,
		)

		provisional_accounting_for_non_stock_items = cint(
			frappe.db.get_value("Company", self.company, "enable_provisional_accounting_for_non_stock_items")
		)

		exchange_rate_map, net_rate_map = get_purchase_document_details(self)

		def validate_account(account_type):
			frappe.throw(_("{0} account not found while submitting purchase receipt").format(account_type))

		def make_item_asset_inward_gl_entry(item, stock_value_diff, stock_asset_account_name):
			account_currency = get_account_currency(stock_asset_account_name)

			if not stock_asset_account_name:
				validate_account("Asset or warehouse account")

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=stock_asset_account_name,
				cost_center=d.cost_center,
				debit=stock_value_diff,
				credit=0.0,
				remarks=remarks,
				against_account=stock_asset_rbnb,
				account_currency=account_currency,
				item=item,
			)

		def make_stock_received_but_not_billed_entry(item):
			if (
				self.get("is_return")
				and item.return_qty_from_rejected_warehouse
				and not frappe.db.get_single_value(
					"Buying Settings", "set_valuation_rate_for_rejected_materials"
				)
			):
				return 0.0

			account = stock_asset_rbnb
			if item.from_warehouse:
				_inv_dict = self.get_inventory_account_dict(item, inventory_account_map, "from_warehouse")
				account = _inv_dict["account"]

			account_currency = get_account_currency(account)

			# GL Entry for from warehouse or Stock Received but not billed
			# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
			credit_amount = (
				flt(item.base_net_amount, item.precision("base_net_amount"))
				if account_currency == self.company_currency
				else flt(item.net_amount, item.precision("net_amount"))
			)

			outgoing_amount = item.base_net_amount
			if self.is_internal_transfer() and item.valuation_rate:
				outgoing_amount = abs(get_stock_value_difference(self.name, item.name, item.from_warehouse))
				credit_amount = outgoing_amount

			if item.get("rejected_qty") and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				outgoing_amount += get_stock_value_difference(self.name, item.name, item.rejected_warehouse)
				credit_amount = outgoing_amount

			if credit_amount:
				if not account:
					validate_account("Stock or Asset Received But Not Billed")

				self.add_gl_entry(
					gl_entries=gl_entries,
					account=account,
					cost_center=item.cost_center,
					debit=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
					credit=0.0,
					remarks=remarks,
					against_account=stock_asset_account_name,
					debit_in_account_currency=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
					account_currency=account_currency,
					item=item,
				)

				# check if the exchange rate has changed
				if d.get("purchase_invoice"):
					if (
						exchange_rate_map[item.purchase_invoice]
						and self.conversion_rate != exchange_rate_map[item.purchase_invoice]
						and item.net_rate == net_rate_map[item.purchase_invoice_item]
					):
						discrepancy_caused_by_exchange_rate_difference = (item.qty * item.net_rate) * (
							exchange_rate_map[item.purchase_invoice] - self.conversion_rate
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=discrepancy_caused_by_exchange_rate_difference,
							remarks=remarks,
							against_account=self.supplier,
							debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
							account_currency=account_currency,
							item=item,
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=self.get_company_default("exchange_gain_loss_account"),
							cost_center=d.cost_center,
							debit=discrepancy_caused_by_exchange_rate_difference,
							credit=0.0,
							remarks=remarks,
							against_account=self.supplier,
							debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
							account_currency=account_currency,
							item=item,
						)

			return outgoing_amount

		def make_landed_cost_gl_entries(item):
			# Amount added through landed-cost-voucher
			if item.landed_cost_voucher_amount and landed_cost_entries:
				if (item.item_code, item.name) in landed_cost_entries:
					for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
						account_currency = get_account_currency(account)
						credit_amount = (
							flt(amount["base_amount"])
							if (amount["base_amount"] or account_currency != self.company_currency)
							else flt(amount["amount"])
						)

						if not account:
							validate_account("Landed Cost Account")

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount,
							remarks=remarks,
							against_account=stock_asset_account_name,
							credit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)

		def make_amount_difference_entry(item):
			if item.amount_difference_with_purchase_invoice and stock_asset_rbnb:
				account_currency = get_account_currency(stock_asset_rbnb)
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=stock_asset_rbnb,
					cost_center=item.cost_center,
					debit=0.0,
					credit=flt(item.amount_difference_with_purchase_invoice),
					remarks=_("Adjustment based on Purchase Invoice rate"),
					against_account=stock_asset_account_name,
					account_currency=account_currency,
					project=item.project,
					item=item,
				)

		def make_sub_contracting_gl_entries(item):
			# sub-contracting warehouse
			if flt(item.rm_supp_cost) and supplier_warehouse_account:
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=supplier_warehouse_account,
					cost_center=item.cost_center,
					debit=0.0,
					credit=flt(item.rm_supp_cost),
					remarks=remarks,
					against_account=stock_asset_account_name,
					account_currency=supplier_warehouse_account_currency,
					item=item,
				)

		def make_divisional_loss_gl_entry(item, outgoing_amount):
			if item.is_fixed_asset:
				return

			# divisional loss adjustment
			valuation_amount_as_per_doc = (
				flt(outgoing_amount, d.precision("base_net_amount"))
				+ flt(item.landed_cost_voucher_amount)
				+ flt(item.rm_supp_cost)
				+ flt(item.item_tax_amount)
				+ flt(item.amount_difference_with_purchase_invoice)
			)

			divisional_loss = flt(
				valuation_amount_as_per_doc - flt(stock_value_diff), item.precision("base_net_amount")
			)

			if item.get("rejected_qty") and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				rejected_item_cost = get_stock_value_difference(self.name, item.name, item.rejected_warehouse)
				divisional_loss -= rejected_item_cost

			if divisional_loss:
				loss_account = (
					self.get_company_default("default_expense_account", ignore_validation=True)
					or stock_asset_rbnb
				)

				cost_center = item.cost_center or frappe.get_cached_value(
					"Company", self.company, "cost_center"
				)
				account_currency = get_account_currency(loss_account)
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=loss_account,
					cost_center=cost_center,
					debit=divisional_loss,
					credit=0.0,
					remarks=remarks,
					against_account=stock_asset_account_name,
					account_currency=account_currency,
					project=item.project,
					item=item,
				)

		stock_items = self.get_stock_items()
		warehouse_with_no_account = []

		for d in self.get("items"):
			remarks = self.get("remarks") or _("Accounting Entry for {0}").format(
				"Asset" if d.is_fixed_asset else "Stock"
			)

			if (
				provisional_accounting_for_non_stock_items
				and d.item_code not in stock_items
				and flt(d.qty)
				and d.get("provisional_expense_account")
				and not d.is_fixed_asset
			):
				self.add_provisional_gl_entry(
					d, gl_entries, self.posting_date, d.get("provisional_expense_account")
				)
			elif flt(d.qty) and (flt(d.valuation_rate) or self.is_return):
				if not (
					(erpnext.is_perpetual_inventory_enabled(self.company) and d.item_code in stock_items)
					or (d.is_fixed_asset and not d.purchase_invoice)
				):
					continue

				stock_asset_rbnb = (
					self.get_company_default("asset_received_but_not_billed")
					if d.is_fixed_asset
					else self.get_company_default("stock_received_but_not_billed")
				)
				landed_cost_entries = self.get_item_account_wise_lcv_entries()
				if d.is_fixed_asset:
					stock_asset_account_name = d.expense_account
					stock_value_diff = (
						flt(d.base_net_amount) + flt(d.item_tax_amount) + flt(d.landed_cost_voucher_amount)
					)
				elif inventory_account := self.get_inventory_account_dict(d, inventory_account_map):
					stock_value_diff = get_stock_value_difference(self.name, d.name, d.warehouse)
					stock_asset_account_name = inventory_account["account"]

					supplier_warehouse_account = None
					supplier_warehouse_account_currency = None
					if self.supplier_warehouse:
						if _inv_dict := self.get_inventory_account_dict(
							d, inventory_account_map, "supplier_warehouse"
						):
							supplier_warehouse_account = _inv_dict["account"]
							supplier_warehouse_account_currency = _inv_dict["account_currency"]

					# If PR is sub-contracted and fg item rate is zero
					# in that case if account for source and target warehouse are same,
					# then GL entries should not be posted
					if (
						flt(stock_value_diff) == flt(d.rm_supp_cost)
						and supplier_warehouse_account
						and stock_asset_account_name == supplier_warehouse_account
					):
						continue

				if (flt(d.valuation_rate) or self.is_return or d.is_fixed_asset) and flt(d.qty):
					make_item_asset_inward_gl_entry(d, stock_value_diff, stock_asset_account_name)
					outgoing_amount = make_stock_received_but_not_billed_entry(d)
					make_landed_cost_gl_entries(d)
					make_amount_difference_entry(d)
					make_sub_contracting_gl_entries(d)
					make_divisional_loss_gl_entry(d, outgoing_amount)
			elif (d.warehouse and d.qty and d.warehouse not in warehouse_with_no_account) or (
				not frappe.db.get_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials")
				and d.rejected_warehouse
				and d.rejected_warehouse not in warehouse_with_no_account
			):
				warehouse_with_no_account.append(d.warehouse or d.rejected_warehouse)

			if d.is_fixed_asset and d.landed_cost_voucher_amount:
				self.update_assets(d, d.valuation_rate)

			if d.rejected_qty and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				stock_asset_rbnb = (
					self.get_company_default("asset_received_but_not_billed")
					if d.is_fixed_asset
					else self.get_company_default("stock_received_but_not_billed")
				)

				stock_value_diff = get_stock_value_difference(self.name, d.name, d.rejected_warehouse)
				_inv_dict = self.get_inventory_account_dict(d, inventory_account_map, "rejected_warehouse")

				stock_asset_account_name = _inv_dict["account"]

				make_item_asset_inward_gl_entry(d, stock_value_diff, stock_asset_account_name)
				if not d.qty:
					make_stock_received_but_not_billed_entry(d)

		if warehouse_with_no_account:
			frappe.msgprint(
				_("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)

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

	def make_tax_gl_entries(self, gl_entries, via_landed_cost_voucher=False):
		negative_expense_to_be_booked = sum([flt(d.item_tax_amount) for d in self.get("items")])
		# Cost center-wise amount breakup for other charges included for valuation
		valuation_tax = {}
		for tax in self.get("taxes"):
			if tax.category in ("Valuation", "Valuation and Total") and flt(
				tax.base_tax_amount_after_discount_amount
			):
				if not tax.cost_center:
					frappe.throw(
						_("Cost Center is required in row {0} in Taxes table for type {1}").format(
							tax.idx, _(tax.category)
						)
					)
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(
					tax.base_tax_amount_after_discount_amount
				)

		if negative_expense_to_be_booked and valuation_tax:
			# Backward compatibility:
			# and charges added via Landed Cost Voucher,
			# post valuation related charges on "Stock Received But Not Billed"
			against_accounts = ", ".join([d.account for d in gl_entries if flt(d.debit) > 0])
			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = negative_expense_to_be_booked
			i = 1
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					account = tax.account_head
					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = negative_expense_to_be_booked * (
							valuation_tax[tax.name] / total_valuation_amount
						)
						amount_including_divisional_loss -= applicable_amount

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=account,
						cost_center=tax.cost_center,
						debit=0.0,
						credit=applicable_amount,
						remarks=self.remarks or _("Accounting Entry for Stock"),
						against_account=against_accounts,
						item=tax,
					)

					i += 1

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
		billed_against_po = flt(po_billed_amt_details.get(pr_item.purchase_order_item))

		# Get billed amount directly against Purchase Receipt
		billed_amt_against_pr = flt(pr_items_billed_amount.get(pr_item.name, 0))

		# Distribute billed amount directly against PO between PRs based on FIFO
		if billed_against_po and billed_amt_against_pr < pr_item.amount:
			pending_to_bill = flt(pr_item.amount) - billed_amt_against_pr
			if pending_to_bill <= billed_against_po:
				billed_amt_against_pr += pending_to_bill
				billed_against_po -= pending_to_bill
			else:
				billed_amt_against_pr += billed_against_po
				billed_against_po = 0

		po_billed_amt_details[pr_item.purchase_order_item] = billed_against_po

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
		.select(fn.Sum(purchase_invoice_item.amount).as_("billed_amt"), purchase_invoice_item.po_detail)
		.where(
			(purchase_invoice_item.po_detail.isin(po_items))
			& (purchase_invoice.docstatus == 1)
			& (purchase_invoice_item.pr_detail.isnull())
			& (purchase_invoice.update_stock == 0)
		)
		.groupby(purchase_invoice_item.po_detail)
	).run(as_dict=1)

	return {d.po_detail: flt(d.billed_amt) for d in query}


def update_billing_percentage(pr_doc, update_modified=True, adjust_incoming_rate=False):
	# Update Billing % based on pending accepted qty
	buying_settings = frappe.get_single("Buying Settings")
	over_billing_allowance = frappe.get_single_value("Accounts Settings", "over_billing_allowance")

	total_amount, total_billed_amount, pi_landed_cost_amount = 0, 0, 0
	item_wise_returned_qty = get_item_wise_returned_qty(pr_doc)

	if adjust_incoming_rate:
		item_wise_billed_qty = get_billed_qty_against_purchase_receipt(pr_doc)

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
				and item_wise_billed_qty.get(item.name)
			):
				adjusted_amt = (
					flt(item.billed_amt / item_wise_billed_qty.get(item.name)) - flt(item.rate)
				) * item.qty

			adjusted_amt = flt(adjusted_amt * flt(pr_doc.conversion_rate), item.precision("amount"))
			pi_landed_cost_amount += adjusted_amt
			item.db_set("amount_difference_with_purchase_invoice", adjusted_amt, update_modified=False)
		elif amount and item.billed_amt > amount:
			per_over_billed = (flt(item.billed_amt / amount, 2) * 100) - 100
			if per_over_billed > over_billing_allowance:
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


def get_billed_qty_against_purchase_receipt(pr_doc):
	pr_names = [d.name for d in pr_doc.items]
	table = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(table)
		.select(table.pr_detail, fn.Sum(table.qty).as_("qty"))
		.where((table.pr_detail.isin(pr_names)) & (table.docstatus == 1))
		.groupby(table.pr_detail)
	)
	invoice_data = query.run(as_list=1)

	if not invoice_data:
		return frappe._dict()
	return frappe._dict(invoice_data)


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
def make_purchase_invoice(source_name, target_doc=None, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	from erpnext.accounts.party import get_payment_terms_template

	doc = frappe.get_doc("Purchase Receipt", source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been Invoiced/Returned"))

		doc = frappe.get_doc(target)
		doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
		doc.run_method("onload")
		doc.run_method("set_missing_values")

		if args and args.get("merge_taxes"):
			merge_taxes(source, doc)

		doc.run_method("calculate_taxes_and_totals")
		doc.set_payment_schedule()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty, returned_qty = get_pending_qty(source_doc)
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			target_doc.rejected_qty = 0
		target_doc.stock_qty = flt(target_doc.qty) * flt(
			target_doc.conversion_factor, target_doc.precision("conversion_factor")
		)
		returned_qty_map[source_doc.name] = returned_qty
		target_doc._old_name = source_doc.name

	def get_pending_qty(item_row):
		qty = item_row.qty
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			qty = item_row.received_qty

		pending_qty = qty - invoiced_qty_map.get(item_row.name, 0)

		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			return pending_qty, 0

		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
		if item_row.rejected_qty and returned_qty:
			returned_qty -= item_row.rejected_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		return pending_qty, returned_qty

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doclist = get_mapped_doc(
		"Purchase Receipt",
		source_name,
		{
			"Purchase Receipt": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"supplier_warehouse": "supplier_warehouse",
					"is_return": "is_return",
					"bill_date": "bill_date",
				},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Receipt Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"name": "pr_detail",
					"parent": "purchase_receipt",
					"qty": "received_qty",
					"purchase_order_item": "po_detail",
					"purchase_order": "purchase_order",
					"is_fixed_asset": "is_fixed_asset",
					"asset_location": "asset_location",
					"asset_category": "asset_category",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"filter": lambda d: (
					get_pending_qty(d)[0] <= 0 if not doc.get("is_return") else get_pending_qty(d)[0] > 0
				),
				"condition": select_item,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def get_invoiced_qty_map(purchase_receipt):
	"""returns a map: {pr_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for pr_detail, qty in frappe.db.sql(
		"""select pr_detail, qty from `tabPurchase Invoice Item`
		where purchase_receipt=%s and docstatus=1""",
		purchase_receipt,
	):
		if not invoiced_qty_map.get(pr_detail):
			invoiced_qty_map[pr_detail] = 0
		invoiced_qty_map[pr_detail] += qty

	return invoiced_qty_map


def get_returned_qty_map(purchase_receipt):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(
		frappe.db.sql(
			"""select pr_item.purchase_receipt_item, abs(pr_item.qty) as qty
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent
			and pr.docstatus = 1
			and pr.is_return = 1
			and pr.return_against = %s
	""",
			purchase_receipt,
		)
	)

	return returned_qty_map


@frappe.whitelist()
def make_purchase_return_against_rejected_warehouse(source_name):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Receipt", source_name, return_against_rejected_qty=True)


@frappe.whitelist()
def make_purchase_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Receipt", source_name, target_doc)


@frappe.whitelist()
def update_purchase_receipt_status(docname, status):
	pr = frappe.get_lazy_doc("Purchase Receipt", docname)
	pr.update_status(status)


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Material Transfer"
		target.purpose = "Material Transfer"
		target.set_missing_values()

	doclist = get_mapped_doc(
		"Purchase Receipt",
		source_name,
		{
			"Purchase Receipt": {
				"doctype": "Stock Entry",
			},
			"Purchase Receipt Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"warehouse": "s_warehouse",
					"parent": "reference_purchase_receipt",
					"batch_no": "batch_no",
				},
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_inter_company_delivery_note(source_name, target_doc=None):
	return make_inter_company_transaction("Purchase Receipt", source_name, target_doc)


@erpnext.allow_regional
def update_regional_gl_entries(gl_list, doc):
	return


@frappe.whitelist()
def make_lcv(doctype, docname):
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
