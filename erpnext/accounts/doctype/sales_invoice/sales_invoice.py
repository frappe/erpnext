# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.utils
from frappe import _, msgprint, throw
from frappe.query_builder import Case
from frappe.utils import cint, flt, formatdate, get_link_to_form
from frappe.utils.data import comma_and

import erpnext
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.accounts.doctype.loyalty_program.loyalty_program import validate_loyalty_points
from erpnext.accounts.doctype.pricing_rule.utils import (
	update_coupon_code_count,
	validate_coupon_code,
)
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	validate_docs_for_deferred_accounting,
	validate_docs_for_voucher_types,
)
from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import SalesTaxWithholding
from erpnext.accounts.party import get_due_date, get_party_account
from erpnext.accounts.utils import refresh_subscription_status, update_voucher_outstanding
from erpnext.controllers.accounts_controller import validate_account_head
from erpnext.controllers.selling_controller import SellingController
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.stock.doctype.delivery_note.services.billing_status import (
	update_billed_amount_based_on_so,
)

from .services.fixed_assets import FixedAssetService
from .services.inter_company import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from .services.loyalty import LoyaltyService
from .services.pos import (
	PartialPaymentValidationError,
	POSService,
	get_all_mode_of_payments,
	get_mode_of_payment_info,
	get_mode_of_payments_info,
	update_multi_mode_option,
)
from .services.pos import (
	get_bank_cash_account as _get_bank_cash_account,
)
from .services.status import (
	StatusService,
	get_discounting_status,
	get_total_in_party_account_currency,
	is_overdue,
)
from .services.timesheet_billing import TimesheetBillingService

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class SalesInvoice(SellingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.sales_invoice_advance.sales_invoice_advance import SalesInvoiceAdvance
		from erpnext.accounts.doctype.sales_invoice_item.sales_invoice_item import SalesInvoiceItem
		from erpnext.accounts.doctype.sales_invoice_payment.sales_invoice_payment import SalesInvoicePayment
		from erpnext.accounts.doctype.sales_invoice_timesheet.sales_invoice_timesheet import (
			SalesInvoiceTimesheet,
		)
		from erpnext.accounts.doctype.sales_taxes_and_charges.sales_taxes_and_charges import (
			SalesTaxesandCharges,
		)
		from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import TaxWithholdingEntry
		from erpnext.selling.doctype.sales_team.sales_team import SalesTeam
		from erpnext.stock.doctype.packed_item.packed_item import PackedItem

		account_for_change_amount: DF.Link | None
		additional_discount_account: DF.Link | None
		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		advances: DF.Table[SalesInvoiceAdvance]
		against_income_account: DF.SmallText | None
		allocate_advances_automatically: DF.Check
		amended_from: DF.Link | None
		amount_eligible_for_commission: DF.Currency
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		apply_tds: DF.Check
		auto_repeat: DF.Link | None
		base_change_amount: DF.Currency
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.SmallText | None
		base_net_total: DF.Currency
		base_paid_amount: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		base_write_off_amount: DF.Currency
		cash_bank_account: DF.Link | None
		change_amount: DF.Currency
		commission_rate: DF.Float
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		company_contact_person: DF.Link | None
		company_tax_id: DF.Data | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		coupon_code: DF.Link | None
		currency: DF.Link
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.SmallText | None
		debit_to: DF.Link
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.TextEditor | None
		dispatch_address_name: DF.Link | None
		dont_create_loyalty_points: DF.Check
		due_date: DF.Date | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		has_subcontracted: DF.Check
		ignore_default_payment_terms_template: DF.Check
		ignore_pricing_rule: DF.Check
		ignore_tax_withholding_threshold: DF.Check
		in_words: DF.SmallText | None
		incoterm: DF.Link | None
		inter_company_invoice_reference: DF.Link | None
		is_cash_or_non_trade_discount: DF.Check
		is_consolidated: DF.Check
		is_created_using_pos: DF.Check
		is_debit_note: DF.Check
		is_discounted: DF.Check
		is_internal_customer: DF.Check
		is_opening: DF.Literal["No", "Yes"]
		is_pos: DF.Check
		is_return: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[SalesInvoiceItem]
		language: DF.Link | None
		letter_head: DF.Link | None
		loyalty_amount: DF.Currency
		loyalty_points: DF.Int
		loyalty_program: DF.Link | None
		loyalty_redemption_account: DF.Link | None
		loyalty_redemption_cost_center: DF.Link | None
		named_place: DF.Data | None
		naming_series: DF.Literal["ACC-SINV-.YYYY.-", "ACC-SINV-RET-.YYYY.-"]
		net_total: DF.Currency
		only_include_allocated_payments: DF.Check
		other_charges_calculation: DF.TextEditor | None
		outstanding_amount: DF.Currency
		override_tax_withholding_entries: DF.Check
		packed_items: DF.Table[PackedItem]
		paid_amount: DF.Currency
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		payments: DF.Table[SalesInvoicePayment]
		plc_conversion_rate: DF.Float
		po_date: DF.Date | None
		po_no: DF.Data | None
		pos_closing_entry: DF.Link | None
		pos_profile: DF.Link | None
		posting_date: DF.Date
		posting_time: DF.Time | None
		price_list_currency: DF.Link
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		redeem_loyalty_points: DF.Check
		remarks: DF.SmallText | None
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
		shipping_address: DF.TextEditor | None
		shipping_address_name: DF.Link | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Return",
			"Credit Note Issued",
			"Submitted",
			"Paid",
			"Partly Paid",
			"Unpaid",
			"Unpaid and Discounted",
			"Partly Paid and Discounted",
			"Overdue and Discounted",
			"Overdue",
			"Cancelled",
			"Internal Transfer",
		]
		subscription: DF.Link | None
		tax_category: DF.Link | None
		tax_id: DF.Data | None
		tax_withholding_entries: DF.Table[TaxWithholdingEntry]
		tax_withholding_group: DF.Link | None
		taxes: DF.Table[SalesTaxesandCharges]
		taxes_and_charges: DF.Link | None
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		territory: DF.Link | None
		timesheets: DF.Table[SalesInvoiceTimesheet]
		title: DF.Data | None
		to_date: DF.Date | None
		total: DF.Currency
		total_advance: DF.Currency
		total_billing_amount: DF.Currency
		total_billing_hours: DF.Float
		total_commission: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		unrealized_profit_loss_account: DF.Link | None
		update_billed_amount_in_delivery_note: DF.Check
		update_billed_amount_in_sales_order: DF.Check
		update_outstanding_for_self: DF.Check
		update_stock: DF.Check
		use_company_roundoff_cost_center: DF.Check
		utm_campaign: DF.Link | None
		utm_content: DF.Data | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		write_off_account: DF.Link | None
		write_off_amount: DF.Currency
		write_off_cost_center: DF.Link | None
		write_off_outstanding_amount_automatically: DF.Check
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Sales Invoice Item",
				"target_field": "billed_amt",
				"target_ref_field": "amount",
				"target_dt": "Sales Order Item",
				"join_field": "so_detail",
				"target_parent_dt": "Sales Order",
				"target_parent_field": "per_billed",
				"source_field": "amount",
				"percent_join_field": "sales_order",
				"status_field": "billing_status",
				"keyword": "Billed",
				"overflow_type": "billing",
			}
		]

	def set_indicator(self):
		"""Set indicator for portal"""
		StatusService(self).set_indicator()

	def onload(self):
		super().onload()
		if self.customer:
			tax_withholding_category, tax_withholding_group = frappe.get_cached_value(
				"Customer", self.customer, ["tax_withholding_category", "tax_withholding_group"]
			)
			self.set_onload("apply_tds", tax_withholding_category or tax_withholding_group)

	def validate(self):
		self.validate_auto_set_posting_time()
		super().validate()

		self.is_subcontracted()

		if not (self.is_pos or self.is_debit_note):
			self.so_dn_required()

		SalesTaxWithholding(self).on_validate()

		self.validate_proj_cust()
		POSService(self).validate_pos_return()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.check_sales_order_on_hold_or_close("sales_order")
		self.validate_debit_to_acc()
		self.validate_debit_note_with_update_stock()
		self.clear_unallocated_advances("Sales Invoice Advance", "advances")
		FixedAssetService(self).validate_fixed_asset()
		FixedAssetService(self).set_income_account_for_fixed_assets()
		self.validate_item_cost_centers()
		self.check_conversion_rate()
		self.validate_accounts()

		validate_inter_company_party(
			self.doctype, self.customer, self.company, self.inter_company_invoice_reference
		)

		if self.coupon_code:
			validate_coupon_code(self.coupon_code)

		if cint(self.is_pos):
			self.validate_pos()

		if cint(self.is_created_using_pos):
			POSService(self).validate_created_using_pos()
			POSService(self).validate_full_payment()

		self.validate_dropship_item()

		if cint(self.update_stock):
			self.validate_warehouse()
			self.update_current_stock()

		self.validate_delivery_note()

		if any(d.get("enable_deferred_revenue") for d in self.get("items")):
			validate_service_stop_date(self)

		if not self.is_opening:
			self.is_opening = "No"

		self.set_against_income_account()

		if self.is_return and not self.return_against and self.timesheets:
			frappe.throw(_("Direct return is not allowed for Timesheet."))

		if not self.is_return:
			TimesheetBillingService(self).validate_time_sheets_are_submitted()

		from erpnext.accounts.services.billing_validation import BillingValidationService

		BillingValidationService(self).validate_multiple_billing("Delivery Note", "dn_detail", "amount")

		if self.is_return and self.return_against:
			for row in self.timesheets:
				if row.billing_hours:
					row.billing_hours = -abs(row.billing_hours)
				if row.billing_amount:
					row.billing_amount = -abs(row.billing_amount)

		self.validate_update_stock_for_pick_list_reference()
		self.set_serial_and_batch_bundle_from_pick_list()
		self.update_packing_list()
		TimesheetBillingService(self).set_billing_hours_and_amount()
		TimesheetBillingService(self).update_timesheet_billing_for_project()
		self.set_status()
		if self.is_pos and not self.is_return:
			POSService(self).verify_payment_amount_is_positive()

		if self.is_pos and self.is_return:
			POSService(self).verify_payment_amount_is_negative()

		if self.redeem_loyalty_points and self.loyalty_points and not self.is_consolidated:
			validate_loyalty_points(self, self.loyalty_points)

		POSService(self).allow_write_off_only_on_pos()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.validate_subcontracted_sales_order()
		self.validate_scio_self_rm_qty()

	def validate_update_stock_for_pick_list_reference(self):
		if self.update_stock or self.is_return:
			return

		for row in self.items:
			if row.get("against_pick_list"):
				frappe.throw(
					_(
						"Row {0}: Update Stock must be checked for item {1} because it is against Pick List {2}."
					).format(row.idx, frappe.bold(row.item_code), frappe.bold(row.against_pick_list))
				)

	def validate_accounts(self):
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_income_account()

	def validate_for_repost(self):
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_income_account()
		validate_docs_for_voucher_types(["Sales Invoice"])
		validate_docs_for_deferred_accounting([self.name], [])

	def validate_item_cost_centers(self):
		for item in self.items:
			item.validate_cost_center(self.company)

	def validate_income_account(self):
		for item in self.get("items"):
			validate_account_head(item.idx, item.income_account, self.company, _("Income"))

	def before_save(self):
		POSService(self).update_paid_amount()
		POSService(self).set_account_for_mode_of_payment()

	def before_submit(self):
		self.add_remarks()

	def on_submit(self):
		POSService(self).validate_pos_paid_amount()

		if not self.auto_repeat:
			frappe.get_cached_doc("Authorization Control").validate_approving_authority(
				self.doctype, self.company, self.base_grand_total, self
			)

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		SalesTaxWithholding(self).on_submit()

		self.update_status_updater_args()
		self.update_prevdoc_status()

		self.update_billing_status_in_dn()
		self.clear_unallocated_mode_of_payments()

		if self.update_stock == 1:
			for table_name in ["items", "packed_items"]:
				if not self.get(table_name):
					continue

				self.make_bundle_for_sales_purchase_return(table_name)
				self.make_bundle_using_old_serial_batch_fields(table_name)

			self.validate_standalone_serial_nos_customer()
			self.update_stock_reservation_entries()
			self.update_stock_ledger()

		FixedAssetService(self).split_asset_based_on_sale_qty()
		FixedAssetService(self).process_asset_depreciation()

		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()
			self.update_pick_list_status()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.check_credit_limit()

		if cint(self.is_pos) != 1 and not self.is_return:
			self.update_against_document_in_jv()

		TimesheetBillingService(self).update_time_sheet(
			None if (self.is_return and self.return_against) else self.name
		)

		if frappe.get_single_value("Selling Settings", "sales_update_frequency") == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		if self.coupon_code:
			update_coupon_code_count(self.coupon_code, "used")

		if (
			not self.is_return
			and not self.is_consolidated
			and self.loyalty_program
			and not self.dont_create_loyalty_points
		):
			LoyaltyService(self).make_loyalty_point_entry()
		elif self.is_return and self.return_against and not self.is_consolidated and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			LoyaltyService(against_si_doc).delete_loyalty_point_entry()
			LoyaltyService(against_si_doc).make_loyalty_point_entry()
		if self.redeem_loyalty_points and not self.is_consolidated and self.loyalty_points:
			LoyaltyService(self).apply_loyalty_points()

		self.process_common_party_accounting()
		self.update_billed_qty_in_scio()

		if self.is_return:
			self.refresh_subscription_status()

	def before_cancel(self):
		POSService(self).check_if_created_using_pos_and_pos_closing_entry_generated()
		POSService(self).check_if_consolidated_invoice()

		super().before_cancel()
		TimesheetBillingService(self).update_time_sheet(
			self.return_against if (self.is_return and self.return_against) else None
		)

	def on_cancel(self):
		check_if_return_invoice_linked_with_payment_entry(self)

		super().on_cancel()

		self.check_sales_order_on_hold_or_close("sales_order")

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_in_dn()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")

		SalesTaxWithholding(self).on_cancel()
		if self.update_stock == 1:
			self.update_stock_ledger()

		FixedAssetService(self).process_asset_depreciation()

		self.make_gl_entries_on_cancel()

		if self.update_stock == 1:
			self.update_stock_reservation_entries()
			self.repost_future_sle_and_gle()
			self.update_pick_list_status()

		self.db_set("status", "Cancelled")

		if self.coupon_code:
			update_coupon_code_count(self.coupon_code, "cancelled")

		if frappe.get_single_value("Selling Settings", "sales_update_frequency") == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()

		if not self.is_return and not self.is_consolidated and self.loyalty_program:
			LoyaltyService(self).delete_loyalty_point_entry()
		elif self.is_return and self.return_against and not self.is_consolidated and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			LoyaltyService(against_si_doc).delete_loyalty_point_entry()
			LoyaltyService(against_si_doc).make_loyalty_point_entry()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		TimesheetBillingService(self).unlink_sales_invoice_from_timesheets()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Repost Payment Ledger",
			"Repost Payment Ledger Items",
			"Repost Accounting Ledger",
			"Repost Accounting Ledger Items",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Payment Ledger Entry",
			"Serial and Batch Bundle",
			"Tax Withholding Entry",
		)

		self.delete_auto_created_batches()

		if (
			self.doctype == "Sales Invoice"
			and self.is_pos
			and self.is_return
			and self.is_created_using_pos
			and not self.pos_closing_entry
		):
			POSService(self).cancel_pos_invoice_credit_note_generated_during_sales_invoice_mode()

		self.update_billed_qty_in_scio()
		self.refresh_subscription_status()

	def update_status_updater_args(self):
		if not cint(self.update_stock):
			return

		self.status_updater.extend(
			[
				{
					"source_dt": "Sales Invoice Item",
					"target_dt": "Sales Order Item",
					"target_parent_dt": "Sales Order",
					"target_parent_field": "per_delivered",
					"target_field": "delivered_qty",
					"target_ref_field": "qty",
					"source_field": "qty",
					"join_field": "so_detail",
					"percent_join_field": "sales_order",
					"status_field": "delivery_status",
					"keyword": "Delivered",
					"second_source_dt": "Delivery Note Item",
					"second_source_field": "qty",
					"second_join_field": "so_detail",
					"overflow_type": "delivery",
					"extra_cond": """ and exists(select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and update_stock = 1)""",
				},
				{
					"source_dt": "Sales Invoice Item",
					"target_dt": "Pick List Item",
					"join_field": "pick_list_item",
					"target_field": "delivered_qty",
					"target_parent_dt": "Pick List",
					"target_parent_field": "per_delivered",
					"target_ref_field": "picked_qty",
					"source_field": "stock_qty",
					"percent_join_field": "against_pick_list",
					"status_field": "delivery_status",
					"keyword": "Delivered",
				},
			]
		)

		if not cint(self.is_return):
			return

		self.status_updater.append(
			{
				"source_dt": "Sales Invoice Item",
				"target_dt": "Sales Order Item",
				"join_field": "so_detail",
				"target_field": "returned_qty",
				"target_parent_dt": "Sales Order",
				"source_field": "-1 * qty",
				"second_source_dt": "Delivery Note Item",
				"second_source_field": "-1 * qty",
				"second_join_field": "so_detail",
				"extra_cond": """ and exists (select name from `tabSales Invoice` where name=`tabSales Invoice Item`.parent and update_stock=1 and is_return=1)""",
			}
		)

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = frappe.db.get_value(
			"Customer Credit Limit",
			filters={"parent": self.customer, "parenttype": "Customer", "company": self.company},
			fieldname=["bypass_credit_limit_check"],
		)

		if bypass_credit_limit_check_at_sales_order:
			validate_against_credit_limit = True

		for d in self.get("items"):
			if not (d.sales_order or d.delivery_note):
				validate_against_credit_limit = True
				break
		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company, bypass_credit_limit_check_at_sales_order)

	@frappe.whitelist()
	def set_missing_values(self, for_validate: bool = False):
		pos = POSService(self).set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			self.party_account_currency = frappe.db.get_value(
				"Account", self.debit_to, "account_currency", cache=True
			)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(
				self.posting_date,
				"Customer",
				self.customer,
				self.company,
				template_name=self.payment_terms_template,
			)

		super().set_missing_values(for_validate)

		print_format = pos.get("print_format") if pos else None
		if not print_format and not cint(frappe.db.get_value("Print Format", "POS Invoice", "disabled")):
			print_format = "POS Invoice"

		if pos:
			return {
				"print_format": print_format,
				"allow_edit_rate": pos.get("allow_user_to_edit_rate"),
				"allow_edit_discount": pos.get("allow_user_to_edit_discount"),
				"utm_source": pos.get("utm_source"),
				"utm_campaign": pos.get("utm_campaign"),
				"utm_medium": pos.get("utm_medium"),
				"allow_print_before_pay": pos.get("allow_print_before_pay"),
				"set_default_payment": pos.get("set_grand_total_to_default_mop", 1),
			}

	# Called by POS Invoice
	def set_pos_fields(self, for_validate=False):
		return POSService(self).set_pos_fields(for_validate)

	def refresh_subscription_status(self):
		if self.get("subscription"):
			refresh_subscription_status(self.subscription)

	@frappe.whitelist()
	def reset_mode_of_payments(self):
		POSService(self).reset_mode_of_payments()

	@frappe.whitelist()
	def set_account_for_mode_of_payment(self):
		POSService(self).set_account_for_mode_of_payment()

	# Called by POS Invoice
	def validate_pos(self):
		POSService(self).validate_pos()

	# Called by POS Invoice
	def validate_pos_opening_entry(self):
		POSService(self).validate_pos_opening_entry()

	# Called by POS Invoice
	def clear_unallocated_mode_of_payments(self):
		POSService(self).clear_unallocated_mode_of_payments()

	# Called by POS Invoice
	def validate_full_payment(self):
		POSService(self).validate_full_payment()

	def get_company_abbr(self):
		return frappe.db.get_value("Company", self.company, "abbr")

	def validate_debit_to_acc(self):
		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			if not self.debit_to:
				self.raise_missing_debit_credit_account_error("Customer", self.customer)

		account = frappe.get_cached_value(
			"Account", self.debit_to, ["account_type", "report_type", "account_currency"], as_dict=True
		)

		if not account:
			frappe.throw(_("Debit To is required"), title=_("Account Missing"))

		if account.report_type != "Balance Sheet":
			msg = (
				_("Please ensure {0} account is a Balance Sheet account.").format(frappe.bold(_("Debit To")))
				+ " "
			)
			msg += _(
				"You can change the parent account to a Balance Sheet account or select a different account."
			)
			frappe.throw(msg, title=_("Invalid Account"))

		if self.customer and account.account_type != "Receivable":
			msg = (
				_("Please ensure {0} account {1} is a Receivable account.").format(
					frappe.bold(_("Debit To")), frappe.bold(self.debit_to)
				)
				+ " "
			)
			msg += _("Change the account type to Receivable or select a different account.")
			frappe.throw(msg, title=_("Invalid Account"))

		self.party_account_currency = account.account_currency

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Sales Order": {
					"ref_dn_field": "sales_order",
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
				"Delivery Note": {
					"ref_dn_field": "delivery_note",
					"compare_fields": [
						["customer", "="],
						["company", "="],
						["project", "="],
						["currency", "="],
					],
				},
				"Delivery Note Item": {
					"ref_dn_field": "dn_detail",
					"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
			}
		)

		if (
			cint(frappe.get_single_value("Selling Settings", "maintain_same_sales_rate"))
			and not self.is_return
			and not self.is_internal_customer
		):
			self.validate_rate_with_reference_doc(
				[["Sales Order", "sales_order", "so_detail"], ["Delivery Note", "delivery_note", "dn_detail"]]
			)

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get("items"):
			if d.income_account and d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.against_income_account = ",".join(against_acc)

	def force_set_against_income_account(self):
		self.set_against_income_account()
		frappe.db.set_value(self.doctype, self.name, "against_income_account", self.against_income_account)

	def add_remarks(self):
		if not self.remarks:
			if self.po_no:
				self.remarks = _("Against Customer Order {0}").format(self.po_no)
				if self.po_date:
					self.remarks += " " + _("dated {0}").format(formatdate(self.po_date))

	def validate_auto_set_posting_time(self):
		if self.is_new() and self.amended_from:
			self.set_posting_time = 1

		self.validate_posting_time()

	def so_dn_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		if self.is_return:
			return

		prev_doc_field_map = {
			"Sales Order": ["so_required", "is_pos"],
			"Delivery Note": ["dn_required", "update_stock"],
		}
		for key, value in prev_doc_field_map.items():
			if frappe.get_single_value("Selling Settings", value[0]) == "Yes":
				if frappe.get_value("Customer", self.customer, value[0]):
					continue

				for d in self.get("items"):
					if d.item_code and not d.get(key.lower().replace(" ", "_")) and not self.get(value[1]):
						msgprint(
							_("{0} is mandatory for Item {1}").format(key, d.item_code), raise_exception=1
						)

	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			Project = frappe.qb.DocType("Project")

			query = (
				frappe.qb.from_(Project)
				.select(Project.name)
				.where(Project.name == self.project)
				.where(
					(Project.customer == self.customer)
					| (Project.customer.isnull())
					| (Project.customer == "")
				)
			)

			if not query.run():
				throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

	def validate_warehouse(self):
		super().validate_warehouse()

		for d in self.get_item_list():
			if (
				not d.warehouse
				and d.item_code
				and frappe.get_cached_value("Item", d.item_code, "is_stock_item")
			):
				frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

	def validate_delivery_note(self):
		"""If items are linked with a delivery note, stock cannot be updated again."""
		if not cint(self.update_stock):
			return

		notes = [item.delivery_note for item in self.items if item.delivery_note]
		if notes:
			frappe.throw(
				_("Stock cannot be updated against the following Delivery Notes: {0}").format(
					comma_and(notes)
				),
			)

	def validate_subcontracted_sales_order(self):
		if self.has_subcontracted:
			if [item for item in self.items if not item.sales_order and not item.scio_detail]:
				frappe.throw(
					_(
						"All items must be linked to a Sales Order or Subcontracting Inward Order for this Sales Invoice."
					)
				)
			if not all(
				frappe.get_all(
					"Sales Order",
					{"name": ["in", [item.sales_order for item in self.items if item.sales_order]]},
					pluck="is_subcontracted",
				)
			):
				frappe.throw(_("All linked Sales Orders must be subcontracted."))

	def validate_scio_self_rm_qty(self):
		self_rms = [item for item in self.items if item.scio_detail]
		if self_rms:
			table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
			query = (
				frappe.qb.from_(table)
				.select(table.required_qty, table.consumed_qty, table.billed_qty, table.name)
				.where((table.docstatus == 1) & (table.name.isin([item.scio_detail for item in self_rms])))
			)
			result = query.run(as_dict=True)
			data = {item.name: item for item in result}
			for item in self_rms:
				row = data.get(item.scio_detail)
				max_qty = max(row.required_qty, row.consumed_qty) - row.billed_qty
				if item.stock_qty > max_qty:
					frappe.throw(
						_("Row #{0}: Stock quantity {1} ({2}) for item {3} cannot exceed {4}").format(
							item.idx,
							item.stock_qty,
							item.stock_uom,
							get_link_to_form("Item", item.item_code),
							frappe.bold(max_qty),
						)
					)

	def validate_write_off_account(self):
		if flt(self.write_off_amount) and not self.write_off_account:
			self.write_off_account = frappe.get_cached_value("Company", self.company, "write_off_account")

		if flt(self.write_off_amount) and not self.write_off_account:
			msgprint(_("Please enter Write Off Account"), raise_exception=1)

	def validate_account_for_change_amount(self):
		if flt(self.change_amount) and not self.account_for_change_amount:
			msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def validate_debit_note_with_update_stock(self):
		"""Prevent stock update when Sales Invoice is marked as Debit Note."""
		if self.is_debit_note and cint(self.update_stock):
			frappe.throw(
				_(
					"You cannot update stock for a Debit Note. A Debit Note is a financial "
					"document that should not affect inventory. Please disable 'Update Stock'."
				),
				title=_("Invalid Configuration"),
			)

	def validate_dropship_item(self):
		"""If items are drop shipped, stock cannot be updated."""
		if not cint(self.update_stock):
			return

		if any(item.delivered_by_supplier for item in self.items):
			frappe.throw(
				_(
					"Stock cannot be updated because the invoice contains a drop shipping item. Please disable 'Update Stock' or remove the drop shipping item."
				),
			)

	def update_current_stock(self):
		for item in self.items:
			item.set_actual_qty()

		for packed_item in self.packed_items:
			packed_item.set_actual_and_projected_qty()

	def update_packing_list(self):
		if cint(self.update_stock) == 1:
			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

			make_packing_list(self)
		else:
			self.set("packed_items", [])

	@frappe.whitelist()
	def is_auto_fetch_timesheet_enabled(self):
		return frappe.db.get_single_value("Projects Settings", "fetch_timesheet_in_sales_invoice")

	@frappe.whitelist()
	def add_timesheet_data(self):
		TimesheetBillingService(self).add_timesheet_data()

	def check_prev_docstatus(self):
		for d in self.get("items"):
			if (
				d.sales_order
				and frappe.db.get_value("Sales Order", d.sales_order, "docstatus", cache=True) != 1
			):
				frappe.throw(_("Sales Order {0} is not submitted").format(d.sales_order))

			if (
				d.delivery_note
				and frappe.db.get_value("Delivery Note", d.delivery_note, "docstatus", cache=True) != 1
			):
				throw(_("Delivery Note {0} is not submitted").format(d.delivery_note))

	def make_gl_entries(self, gl_entries=None, from_repost=False):
		from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
		if not gl_entries:
			gl_entries = self.get_gl_entries()

		if gl_entries:
			update_outstanding = (
				"No"
				if (cint(self.is_pos) or self.write_off_account or cint(self.redeem_loyalty_points))
				else "Yes"
			)

			if self.docstatus == 1:
				make_gl_entries(
					gl_entries,
					update_outstanding=update_outstanding,
					merge_entries=False,
					from_repost=from_repost,
				)

				self.make_exchange_gain_loss_journal()
			elif self.docstatus == 2:
				make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

			if update_outstanding == "No":
				update_voucher_outstanding(
					voucher_type=self.doctype,
					voucher_no=self.return_against
					if cint(self.is_return) and self.return_against
					else self.name,
					account=self.debit_to,
					party_type="Customer",
					party=self.customer,
				)

		elif self.docstatus == 2 and cint(self.update_stock) and cint(auto_accounting_for_stock):
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(self, inventory_account_map=None):
		from erpnext.accounts.doctype.sales_invoice.services.gl_composer import SalesInvoiceGLComposer

		return SalesInvoiceGLComposer(self).compose(inventory_account_map)

	@property
	def enable_discount_accounting(self):
		if not hasattr(self, "_enable_discount_accounting"):
			self._enable_discount_accounting = cint(
				frappe.get_single_value("Selling Settings", "enable_discount_accounting")
			)

		return self._enable_discount_accounting

	def update_billing_status_in_dn(self, update_modified=True):
		if self.is_return and not self.update_billed_amount_in_delivery_note:
			return

		updated_delivery_notes = []

		SalesInvoiceItem = frappe.qb.DocType("Sales Invoice Item")
		from frappe.query_builder.functions import Coalesce, Sum

		for d in self.get("items"):
			if d.dn_detail:
				query = (
					frappe.qb.from_(SalesInvoiceItem)
					.select(Coalesce(Sum(SalesInvoiceItem.amount), 0))
					.where(SalesInvoiceItem.dn_detail == d.dn_detail)
					.where(SalesInvoiceItem.docstatus == 1)
				)

				res = query.run()
				billed_amt = res[0][0] if res else 0

				frappe.db.set_value(
					"Delivery Note Item",
					d.dn_detail,
					"billed_amt",
					billed_amt,
					update_modified=update_modified,
				)
				updated_delivery_notes.append(d.delivery_note)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			frappe.get_doc("Delivery Note", dn).update_billing_percentage(update_modified=update_modified)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.set("write_off_amount", reference_doc.get("write_off_amount"))
		self.due_date = None

	def update_project(self):
		unique_projects = list(set([d.project for d in self.get("items") if d.project]))
		if self.project and self.project not in unique_projects:
			unique_projects.append(self.project)

		for p in unique_projects:
			project = frappe.get_doc("Project", p)
			project.update_billed_amount()
			project.calculate_gross_margin()
			project.db_update()

	def update_billed_qty_in_scio(self):
		if self.is_return:
			return

		table = frappe.qb.DocType("Subcontracting Inward Order Received Item")
		data = frappe._dict(
			{
				item.scio_detail: item.stock_qty if self._action == "submit" else -item.stock_qty
				for item in self.items
				if item.scio_detail
			}
		)

		if data:
			case_expr = Case()
			for name, qty in data.items():
				case_expr = case_expr.when(table.name == name, table.billed_qty + qty)
			frappe.qb.update(table).set(table.billed_qty, case_expr).where(
				(table.name.isin(list(data.keys()))) & (table.docstatus == 1)
			).run()

	def on_update_after_submit(self):
		fields_to_check = [
			"additional_discount_account",
			"cash_bank_account",
			"account_for_change_amount",
			"write_off_account",
			"loyalty_redemption_account",
			"unrealized_profit_loss_account",
			"is_opening",
		]
		child_tables = {
			"items": ("income_account", "expense_account", "discount_account"),
			"taxes": ("account_head",),
		}
		self.needs_repost = self.check_if_fields_updated(fields_to_check, child_tables)
		if self.needs_repost:
			self.validate_for_repost()
			self.repost_accounting_entries()

	def set_status(self, update=False, status=None, update_modified=True):
		StatusService(self).set_status(update, status, update_modified)

	@frappe.whitelist()
	def is_subcontracted(self):
		if not self.has_subcontracted:
			self.has_subcontracted = bool(
				frappe.get_cached_value(
					"Sales Order",
					{
						"name": ["in", [item.sales_order for item in self.items if item.sales_order]],
						"is_subcontracted": 1,
					},
					"name",
				)
			)
		if self.has_subcontracted:
			self.update_stock = 0
		return self.has_subcontracted


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Invoices"),
			"list_template": "templates/includes/list/list.html",
		}
	)
	return list_context


@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries


@frappe.whitelist()
def get_bank_cash_account(mode_of_payment: str, company: str) -> dict:
	return _get_bank_cash_account(mode_of_payment, company)


@frappe.whitelist()
def get_loyalty_programs(customer: str) -> list:
	from .services.loyalty import get_loyalty_programs as _get

	return _get(customer)


def check_if_return_invoice_linked_with_payment_entry(self):
	if not frappe.get_single_value("Accounts Settings", "unlink_payment_on_cancellation_of_invoice"):
		return

	if self.is_return and self.return_against:
		invoice = self.return_against
	else:
		invoice = self.name

	PaymentEntry = frappe.qb.DocType("Payment Entry")
	PaymentEntryReference = frappe.qb.DocType("Payment Entry Reference")

	query = (
		frappe.qb.from_(PaymentEntry)
		.join(PaymentEntryReference)
		.on(PaymentEntry.name == PaymentEntryReference.parent)
		.select(PaymentEntry.name)
		.where(PaymentEntry.docstatus == 1)
		.where(PaymentEntryReference.reference_name == invoice)
		.where(PaymentEntryReference.allocated_amount < 0)
	)

	payment_entries = query.run(pluck=True)

	links_to_pe = []
	if payment_entries:
		for payment in payment_entries:
			payment_entry = frappe.get_doc("Payment Entry", payment)
			if len(payment_entry.references) > 1:
				links_to_pe.append(payment_entry.name)

		if links_to_pe:
			payment_entries_link = [
				get_link_to_form("Payment Entry", name, label=name) for name in links_to_pe
			]
			message = _("Please cancel and amend the Payment Entry")
			message += " " + ", ".join(payment_entries_link) + " "
			message += _("to unallocate the amount of this Return Invoice before cancelling it.")
			frappe.throw(message)
