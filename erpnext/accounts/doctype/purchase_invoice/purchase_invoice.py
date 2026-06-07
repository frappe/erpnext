# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, formatdate, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.accounts.doctype.purchase_invoice.services.billing_status import BillingStatusService
from erpnext.accounts.doctype.purchase_invoice.services.expense_account import ExpenseAccountService
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	validate_docs_for_deferred_accounting,
	validate_docs_for_voucher_types,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	check_if_return_invoice_linked_with_payment_entry,
	get_total_in_party_account_currency,
	is_overdue,
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import PurchaseTaxWithholding
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
from erpnext.accounts.party import get_due_date, get_party_account
from erpnext.accounts.utils import (
	get_account_currency,
	get_fiscal_year,
	refresh_subscription_status,
	update_voucher_outstanding,
)
from erpnext.assets.doctype.asset.asset import is_cwip_accounting_enabled
from erpnext.controllers.buying_controller import BuyingController


class WarehouseMissingError(frappe.ValidationError):
	pass


form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class PurchaseInvoice(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_wise_tax_detail.item_wise_tax_detail import ItemWiseTaxDetail
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.purchase_invoice_advance.purchase_invoice_advance import (
			PurchaseInvoiceAdvance,
		)
		from erpnext.accounts.doctype.purchase_invoice_item.purchase_invoice_item import PurchaseInvoiceItem
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import (
			PurchaseTaxesandCharges,
		)
		from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import TaxWithholdingEntry
		from erpnext.buying.doctype.purchase_receipt_item_supplied.purchase_receipt_item_supplied import (
			PurchaseReceiptItemSupplied,
		)

		additional_discount_percentage: DF.Float
		address_display: DF.TextEditor | None
		advances: DF.Table[PurchaseInvoiceAdvance]
		against_expense_account: DF.SmallText | None
		allocate_advances_automatically: DF.Check
		amended_from: DF.Link | None
		apply_discount_on: DF.Literal["", "Grand Total", "Net Total"]
		apply_tds: DF.Check
		auto_repeat: DF.Link | None
		base_discount_amount: DF.Currency
		base_grand_total: DF.Currency
		base_in_words: DF.Data | None
		base_net_total: DF.Currency
		base_paid_amount: DF.Currency
		base_rounded_total: DF.Currency
		base_rounding_adjustment: DF.Currency
		base_taxes_and_charges_added: DF.Currency
		base_taxes_and_charges_deducted: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		base_write_off_amount: DF.Currency
		bill_date: DF.Date | None
		bill_no: DF.Data | None
		billing_address: DF.Link | None
		billing_address_display: DF.TextEditor | None
		buying_price_list: DF.Link | None
		cash_bank_account: DF.Link | None
		claimed_landed_cost_amount: DF.Currency
		clearance_date: DF.Date | None
		company: DF.Link | None
		contact_display: DF.SmallText | None
		contact_email: DF.SmallText | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		credit_to: DF.Link
		currency: DF.Link | None
		disable_rounded_total: DF.Check
		discount_amount: DF.Currency
		dispatch_address: DF.Link | None
		dispatch_address_display: DF.TextEditor | None
		due_date: DF.Date | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		hold_comment: DF.SmallText | None
		ignore_default_payment_terms_template: DF.Check
		ignore_pricing_rule: DF.Check
		ignore_tax_withholding_threshold: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		inter_company_invoice_reference: DF.Link | None
		is_internal_supplier: DF.Check
		is_opening: DF.Literal["No", "Yes"]
		is_paid: DF.Check
		is_return: DF.Check
		is_subcontracted: DF.Check
		item_wise_tax_details: DF.Table[ItemWiseTaxDetail]
		items: DF.Table[PurchaseInvoiceItem]
		language: DF.Data | None
		letter_head: DF.Link | None
		mode_of_payment: DF.Link | None
		named_place: DF.Data | None
		naming_series: DF.Literal["ACC-PINV-.YYYY.-", "ACC-PINV-RET-.YYYY.-"]
		net_total: DF.Currency
		on_hold: DF.Check
		only_include_allocated_payments: DF.Check
		other_charges_calculation: DF.TextEditor | None
		outstanding_amount: DF.Currency
		override_tax_withholding_entries: DF.Check
		paid_amount: DF.Currency
		party_account_currency: DF.Link | None
		payment_schedule: DF.Table[PaymentSchedule]
		payment_terms_template: DF.Link | None
		per_received: DF.Percent
		plc_conversion_rate: DF.Float
		posting_date: DF.Date
		posting_time: DF.Time | None
		price_list_currency: DF.Link | None
		pricing_rules: DF.Table[PricingRuleDetail]
		project: DF.Link | None
		rejected_warehouse: DF.Link | None
		release_date: DF.Date | None
		remarks: DF.SmallText | None
		represents_company: DF.Link | None
		return_against: DF.Link | None
		rounded_total: DF.Currency
		rounding_adjustment: DF.Currency
		scan_barcode: DF.Data | None
		select_print_heading: DF.Link | None
		sender: DF.Data | None
		set_from_warehouse: DF.Link | None
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.TextEditor | None
		shipping_rule: DF.Link | None
		status: DF.Literal[
			"",
			"Draft",
			"Return",
			"Debit Note Issued",
			"Submitted",
			"Paid",
			"Partly Paid",
			"Unpaid",
			"Overdue",
			"Cancelled",
			"Internal Transfer",
		]
		subscription: DF.Link | None
		supplied_items: DF.Table[PurchaseReceiptItemSupplied]
		supplier: DF.Link
		supplier_address: DF.Link | None
		supplier_group: DF.Link | None
		supplier_name: DF.Data | None
		supplier_warehouse: DF.Link | None
		tax_category: DF.Link | None
		tax_id: DF.ReadOnly | None
		tax_withholding_entries: DF.Table[TaxWithholdingEntry]
		tax_withholding_group: DF.Link | None
		taxes: DF.Table[PurchaseTaxesandCharges]
		taxes_and_charges: DF.Link | None
		taxes_and_charges_added: DF.Currency
		taxes_and_charges_deducted: DF.Currency
		tc_name: DF.Link | None
		terms: DF.TextEditor | None
		title: DF.Data | None
		to_date: DF.Date | None
		total: DF.Currency
		total_advance: DF.Currency
		total_net_weight: DF.Float
		total_qty: DF.Float
		total_taxes_and_charges: DF.Currency
		unrealized_profit_loss_account: DF.Link | None
		update_billed_amount_in_purchase_order: DF.Check
		update_billed_amount_in_purchase_receipt: DF.Check
		update_outstanding_for_self: DF.Check
		update_stock: DF.Check
		use_company_roundoff_cost_center: DF.Check
		use_transaction_date_exchange_rate: DF.Check
		write_off_account: DF.Link | None
		write_off_amount: DF.Currency
		write_off_cost_center: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Purchase Invoice Item",
				"target_dt": "Purchase Order Item",
				"join_field": "po_detail",
				"target_field": "billed_amt",
				"target_parent_dt": "Purchase Order",
				"target_parent_field": "per_billed",
				"target_ref_field": "amount",
				"source_field": "amount",
				"percent_join_field": "purchase_order",
				"overflow_type": "billing",
			}
		]

	def onload(self):
		super().onload()
		if self.supplier:
			tax_withholding_category, tax_withholding_group = frappe.get_cached_value(
				"Supplier", self.supplier, ["tax_withholding_category", "tax_withholding_group"]
			)
			self.set_onload("apply_tds", tax_withholding_category or tax_withholding_group)

		if self.is_new():
			self.set("tax_withholding_entries", [])

	def before_save(self):
		if not self.on_hold:
			self.release_date = ""

	def invoice_is_blocked(self):
		return self.on_hold and (not self.release_date or self.release_date > getdate(nowdate()))

	def validate(self):
		if not self.is_opening:
			self.is_opening = "No"

		self.validate_posting_time()
		self.validate_posting_date_with_po()

		super().validate()

		if not self.is_return:
			self.po_required()
			self.pr_required()
			self.validate_supplier_invoice()

		# validate cash purchase
		if self.is_paid == 1:
			self.validate_cash()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		self.validate_release_date()
		self.check_conversion_rate()
		self.validate_credit_to_acc()
		self.clear_unallocated_advances("Purchase Invoice Advance", "advances")
		self.check_for_on_hold_or_closed_status(
			"Purchase Order", "purchase_order", exclude_if_field="purchase_receipt"
		)
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		expense_account_service = ExpenseAccountService(self)
		expense_account_service.set_expense_account(for_validate=True)
		expense_account_service.validate_expense_account()
		expense_account_service.set_against_expense_account()
		self.validate_write_off_account()
		self.validate_write_off_cost_center()

		from erpnext.accounts.services.billing_validation import BillingValidationService

		BillingValidationService(self).validate_multiple_billing("Purchase Receipt", "pr_detail", "amount")
		self.set_status()
		self.validate_purchase_receipt_if_update_stock()
		validate_inter_company_party(
			self.doctype, self.supplier, self.company, self.inter_company_invoice_reference
		)
		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")
		PurchaseTaxWithholding(self).on_validate()
		self.set_percentage_received()

	def set_percentage_received(self):
		total_billed_qty = 0.0
		total_received_qty = 0.0
		for row in self.items:
			if row.purchase_receipt and row.pr_detail and row.received_qty:
				total_billed_qty += row.qty
				total_received_qty += row.received_qty

		if total_billed_qty and total_received_qty:
			self.per_received = total_received_qty / total_billed_qty * 100

	def validate_release_date(self):
		if self.release_date and getdate(nowdate()) >= getdate(self.release_date):
			frappe.throw(_("Release date must be in the future"))

	def validate_cash(self):
		if not self.cash_bank_account and flt(self.paid_amount):
			frappe.throw(_("Cash or Bank Account is mandatory for making payment entry"))

		if flt(self.paid_amount) + flt(self.write_off_amount) - flt(
			self.get("rounded_total") or self.grand_total
		) > 1 / (10 ** (self.precision("base_grand_total") + 1)):
			frappe.throw(_("""Paid amount + Write Off Amount can not be greater than Grand Total"""))

	def create_remarks(self):
		if not self.remarks:
			if self.bill_no:
				self.remarks = _("Against Supplier Invoice {0}").format(self.bill_no)
				if self.bill_date:
					self.remarks += " " + _("dated {0}").format(formatdate(self.bill_date))

	def set_missing_values(self, for_validate=False):
		if not self.credit_to:
			self.credit_to = get_party_account("Supplier", self.supplier, self.company)
			self.party_account_currency = frappe.get_cached_value(
				"Account", self.credit_to, "account_currency"
			)
		if not self.due_date:
			self.due_date = get_due_date(
				self.posting_date,
				"Supplier",
				self.supplier,
				self.company,
				self.bill_date,
				template_name=self.payment_terms_template,
			)

		if self.supplier:
			tax_withholding_category, tax_withholding_group = frappe.get_cached_value(
				"Supplier", self.supplier, ["tax_withholding_category", "tax_withholding_group"]
			)
			if not for_validate:
				if tax_withholding_category or tax_withholding_group:
					self.apply_tds = 1

		super().set_missing_values(for_validate)

	def validate_credit_to_acc(self):
		if not self.credit_to:
			self.credit_to = get_party_account("Supplier", self.supplier, self.company)
			if not self.credit_to:
				self.raise_missing_debit_credit_account_error("Supplier", self.supplier)

		account = frappe.get_cached_value(
			"Account", self.credit_to, ["account_type", "report_type", "account_currency"], as_dict=True
		)

		if account.report_type != "Balance Sheet":
			frappe.throw(
				_(
					"Please ensure that the {0} account is a Balance Sheet account. You can change the parent account to a Balance Sheet account or select a different account."
				).format(frappe.bold(_("Credit To"))),
				title=_("Invalid Account"),
			)

		if self.supplier and account.account_type != "Payable":
			frappe.throw(
				_(
					"Please ensure that the {0} account {1} is a Payable account. You can change the account type to Payable or select a different account."
				).format(frappe.bold(_("Credit To")), frappe.bold(self.credit_to)),
				title=_("Invalid Account"),
			)

		self.party_account_currency = account.account_currency

	def validate_with_previous_doc(self):
		super().validate_with_previous_doc(
			{
				"Purchase Order": {
					"ref_dn_field": "purchase_order",
					"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
				},
				"Purchase Order Item": {
					"ref_dn_field": "po_detail",
					"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
					"is_child_table": True,
					"allow_duplicate_prev_row_id": True,
				},
				"Purchase Receipt": {
					"ref_dn_field": "purchase_receipt",
					"compare_fields": [["supplier", "="], ["company", "="], ["currency", "="]],
				},
				"Purchase Receipt Item": {
					"ref_dn_field": "pr_detail",
					"compare_fields": [["project", "="], ["item_code", "="], ["uom", "="]],
					"is_child_table": True,
				},
			}
		)

		if (
			cint(frappe.db.get_single_value("Buying Settings", "maintain_same_rate"))
			and not self.is_return
			and not self.is_internal_supplier
		):
			self.validate_rate_with_reference_doc(
				[
					["Purchase Order", "purchase_order", "po_detail"],
					["Purchase Receipt", "purchase_receipt", "pr_detail"],
				]
			)

	def validate_warehouse(self, for_validate=True):
		if self.update_stock and for_validate:
			stock_items = self.get_stock_items()
			for d in self.get("items"):
				if not d.warehouse and d.item_code in stock_items:
					frappe.throw(
						_(
							"Row No {0}: Warehouse is required. Please set a Default Warehouse for Item {1} and Company {2}"
						).format(d.idx, d.item_code, self.company),
						exc=WarehouseMissingError,
					)

		super().validate_warehouse()

	def validate_item_code(self):
		for d in self.get("items"):
			if not d.item_code:
				frappe.msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def set_expense_account(self, for_validate=False):
		ExpenseAccountService(self).set_expense_account(for_validate)

	def force_set_against_expense_account(self):
		ExpenseAccountService(self).force_set_against_expense_account()

	def po_required(self):
		if (
			frappe.db.get_single_value("Buying Settings", "po_required") == "Yes"
			and not self.is_internal_transfer()
			and not frappe.get_value(
				"Supplier", self.supplier, "allow_purchase_invoice_creation_without_purchase_order"
			)
		):
			for d in self.get("items"):
				if not d.purchase_order:
					msg = _("Purchase Order Required for item {}").format(frappe.bold(d.item_code))
					msg += "<br><br>"
					msg += _(
						"To submit the invoice without purchase order please set {0} as {1} in {2}"
					).format(
						frappe.bold(_("Purchase Order Required")),
						frappe.bold(_("No")),
						get_link_to_form("Buying Settings", "Buying Settings", "Buying Settings"),
					)
					throw(msg, title=_("Mandatory Purchase Order"))

	def pr_required(self):
		if frappe.db.get_single_value("Buying Settings", "pr_required") == "Yes":
			stock_and_asset_items = self.get_stock_items()
			stock_and_asset_items.extend(self.get_asset_items())
			if frappe.get_value(
				"Supplier", self.supplier, "allow_purchase_invoice_creation_without_purchase_receipt"
			):
				return

			for d in self.get("items"):
				if not d.purchase_receipt and d.item_code in stock_and_asset_items:
					msg = _("Purchase Receipt Required for item {}").format(frappe.bold(d.item_code))
					msg += "<br><br>"
					msg += _(
						"To submit the invoice without purchase receipt please set {0} as {1} in {2}"
					).format(
						frappe.bold(_("Purchase Receipt Required")),
						frappe.bold(_("No")),
						get_link_to_form("Buying Settings", "Buying Settings", "Buying Settings"),
					)
					throw(msg, title=_("Mandatory Purchase Receipt"))

	def validate_write_off_account(self):
		if self.write_off_amount and not self.write_off_account:
			throw(_("Please enter Write Off Account"))

		if not self.write_off_account:
			return

		doc = frappe.db.get_value(
			"Account", self.write_off_account, ["report_type", "is_group", "company"], as_dict=True
		)

		if not doc or doc.report_type != "Profit and Loss" or doc.is_group or doc.company != self.company:
			throw(_("Please enter a valid Write Off Account"))

	def validate_write_off_cost_center(self):
		if not self.write_off_cost_center:
			return

		doc = frappe.db.get_value(
			"Cost Center", self.write_off_cost_center, ["is_group", "company"], as_dict=True
		)

		if not doc or doc.is_group or doc.company != self.company:
			throw(_("Please enter a valid Write Off Cost Center"))

	def check_prev_docstatus(self):
		for d in self.get("items"):
			if d.purchase_order:
				submitted = frappe.db.sql(
					"select name from `tabPurchase Order` where docstatus = 1 and name = %s", d.purchase_order
				)
				if not submitted:
					frappe.throw(_("Purchase Order {0} is not submitted").format(d.purchase_order))
			if d.purchase_receipt:
				submitted = frappe.db.sql(
					"select name from `tabPurchase Receipt` where docstatus = 1 and name = %s",
					d.purchase_receipt,
				)
				if not submitted:
					frappe.throw(_("Purchase Receipt {0} is not submitted").format(d.purchase_receipt))

	def update_status_updater_args(self):
		if cint(self.update_stock):
			self.status_updater.append(
				{
					"source_dt": "Purchase Invoice Item",
					"target_dt": "Purchase Order Item",
					"join_field": "po_detail",
					"target_field": "received_qty",
					"target_parent_dt": "Purchase Order",
					"target_parent_field": "per_received",
					"target_ref_field": "qty",
					"source_field": "received_qty",
					"second_source_dt": "Purchase Receipt Item",
					"second_source_field": "received_qty",
					"second_join_field": "purchase_order_item",
					"percent_join_field": "purchase_order",
					"overflow_type": "receipt",
					"extra_cond": """ and exists(select name from `tabPurchase Invoice`
					where name=`tabPurchase Invoice Item`.parent and update_stock = 1)""",
				}
			)
			self.status_updater.append(
				{
					"source_dt": "Purchase Invoice Item",
					"target_dt": "Material Request Item",
					"join_field": "material_request_item",
					"target_field": "received_qty",
					"target_parent_dt": "Material Request",
					"target_parent_field": "per_received",
					"target_ref_field": "stock_qty",
					"source_field": "stock_qty",
					"percent_join_field": "material_request",
				}
			)
			if cint(self.is_return):
				self.status_updater.append(
					{
						"source_dt": "Purchase Invoice Item",
						"target_dt": "Purchase Order Item",
						"join_field": "po_detail",
						"target_field": "returned_qty",
						"source_field": "-1 * qty",
						"second_source_dt": "Purchase Receipt Item",
						"second_source_field": "-1 * qty",
						"second_join_field": "purchase_order_item",
						"overflow_type": "receipt",
						"extra_cond": """ and exists (select name from `tabPurchase Invoice`
						where name=`tabPurchase Invoice Item`.parent and update_stock=1 and is_return=1)""",
					}
				)

	def validate_purchase_receipt_if_update_stock(self):
		if self.update_stock:
			for item in self.get("items"):
				if item.purchase_receipt:
					frappe.throw(
						_(
							"Stock cannot be updated for Purchase Invoice {0} because a Purchase Receipt {1} has already been created for this transaction. Please disable the 'Update Stock' checkbox in the Purchase Invoice and save the invoice."
						).format(self.name, item.purchase_receipt),
						title=_("Stock Update Not Allowed"),
					)

	def validate_for_repost(self):
		self.validate_write_off_account()
		self.validate_write_off_cost_center()
		ExpenseAccountService(self).validate_expense_account()
		validate_docs_for_voucher_types(["Purchase Invoice"])
		validate_docs_for_deferred_accounting([], [self.name])

	def before_submit(self):
		self.create_remarks()

	def on_submit(self):
		super().on_submit()
		PurchaseTaxWithholding(self).on_submit()

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_purchase_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		frappe.get_cached_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		if not self.is_return:
			self.update_against_document_in_jv()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		BillingStatusService(self).update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.make_bundle_for_sales_purchase_return()
			self.make_bundle_using_old_serial_batch_fields()
			self.update_stock_ledger()

		# this sequence because outstanding may get -negative
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction":
			self.update_project()

		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		self.process_common_party_accounting()

		if self.is_return:
			self.refresh_subscription_status()

	def on_update_after_submit(self):
		fields_to_check = [
			"cash_bank_account",
			"write_off_account",
			"unrealized_profit_loss_account",
			"is_opening",
		]
		child_tables = {"items": ("expense_account",), "taxes": ("account_head",)}
		self.needs_repost = self.check_if_fields_updated(fields_to_check, child_tables)
		if self.needs_repost:
			self.validate_for_repost()
			self.repost_accounting_entries()

	def refresh_subscription_status(self):
		if self.get("subscription"):
			refresh_subscription_status(self.subscription)

	def make_gl_entries(self, gl_entries=None, from_repost=False):
		update_outstanding = "No" if (cint(self.is_paid) or self.write_off_account) else "Yes"
		if self.docstatus == 1:
			if not gl_entries:
				gl_entries = self.get_gl_entries()

			if gl_entries:
				make_gl_entries(
					gl_entries,
					update_outstanding=update_outstanding,
					merge_entries=False,
					from_repost=from_repost,
				)
				self.make_exchange_gain_loss_journal()
		elif self.docstatus == 2:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
			BillingStatusService(self).cancel_provisional_entries()

		self.update_supplier_outstanding(update_outstanding)

	def update_supplier_outstanding(self, update_outstanding):
		if update_outstanding == "No":
			update_voucher_outstanding(
				voucher_type=self.doctype,
				voucher_no=self.return_against
				if (cint(self.is_return) and self.return_against)
				else self.name,
				account=self.credit_to,
				party_type="Supplier",
				party=self.supplier,
			)

	def get_gl_entries(self, inventory_account_map=None):
		from erpnext.accounts.doctype.purchase_invoice.services.gl_composer import (
			PurchaseInvoiceGLComposer,
		)

		return PurchaseInvoiceGLComposer(self).compose(inventory_account_map)

	def check_asset_cwip_enabled(self):
		# Check if there exists any item with cwip accounting enabled in it's asset category
		for item in self.get("items"):
			if item.item_code and item.is_fixed_asset:
				asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")
				if is_cwip_accounting_enabled(asset_category):
					return 1
		return 0

	def on_cancel(self):
		check_if_return_invoice_linked_with_payment_entry(self)

		super().on_cancel()
		PurchaseTaxWithholding(self).on_cancel()

		self.check_for_on_hold_or_closed_status(
			"Purchase Order", "purchase_order", exclude_if_field="purchase_receipt"
		)

		if self.is_return and not self.update_billed_amount_in_purchase_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		BillingStatusService(self).update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()
			self.delete_auto_created_batches()

		self.make_gl_entries_on_cancel()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction":
			self.update_project()
		self.db_set("status", "Cancelled")

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)
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

		self.refresh_subscription_status()

	def update_project(self):
		projects = frappe._dict()
		for d in self.items:
			if d.project:
				if self.docstatus == 1:
					projects[d.project] = projects.get(d.project, 0) + d.base_net_amount
				elif self.docstatus == 2:
					projects[d.project] = projects.get(d.project, 0) - d.base_net_amount

		pj = frappe.qb.DocType("Project")
		for proj, value in projects.items():
			res = frappe.qb.from_(pj).select(pj.total_purchase_cost).where(pj.name == proj).for_update().run()
			current_purchase_cost = res and res[0][0] or 0
			# frappe.db.set_value("Project", proj, "total_purchase_cost", current_purchase_cost + value)
			project_doc = frappe.get_lazy_doc("Project", proj)
			project_doc.total_purchase_cost = current_purchase_cost + value
			project_doc.calculate_gross_margin()
			project_doc.db_update()

	def validate_supplier_invoice(self):
		if self.bill_no:
			if cint(frappe.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")):
				fiscal_year = get_fiscal_year(self.posting_date, company=self.company, as_dict=True)

				pi = frappe.db.sql(
					"""select name from `tabPurchase Invoice`
					where
						bill_no = %(bill_no)s
						and supplier = %(supplier)s
						and name != %(name)s
						and docstatus < 2
						and posting_date between %(year_start_date)s and %(year_end_date)s""",
					{
						"bill_no": self.bill_no,
						"supplier": self.supplier,
						"name": self.name,
						"year_start_date": fiscal_year.year_start_date,
						"year_end_date": fiscal_year.year_end_date,
					},
				)

				if pi:
					pi = pi[0][0]

					frappe.throw(
						_("Supplier Invoice No exists in Purchase Invoice {0}").format(
							get_link_to_form("Purchase Invoice", pi)
						)
					)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.due_date = None

	def block_invoice(self, hold_comment=None, release_date=None):
		self.db_set("on_hold", 1)
		self.db_set("hold_comment", cstr(hold_comment))
		self.db_set("release_date", release_date)

	def unblock_invoice(self):
		self.db_set("on_hold", 0)
		self.db_set("release_date", None)

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get("amended_from"):
				self.status = "Draft"
			return

		outstanding_amount = flt(self.outstanding_amount, self.precision("outstanding_amount"))
		total = get_total_in_party_account_currency(self)

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if self.is_internal_transfer():
					self.status = "Internal Transfer"
				elif is_overdue(self, total):
					self.status = "Overdue"
				elif 0 < outstanding_amount < total:
					self.status = "Partly Paid"
				elif outstanding_amount > 0 and getdate(self.due_date) >= getdate():
					self.status = "Unpaid"
				# Check if outstanding amount is 0 due to debit note issued against invoice
				elif self.is_return == 0 and frappe.db.get_value(
					"Purchase Invoice", {"is_return": 1, "return_against": self.name, "docstatus": 1}
				):
					self.status = "Debit Note Issued"
				elif self.is_return == 1:
					self.status = "Return"
				elif outstanding_amount <= 0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set("status", self.status, update_modified=update_modified)


# to get details of purchase invoice/receipt from which this doc was created for exchange rate difference handling
def get_purchase_document_details(doc):
	if doc.doctype == "Purchase Invoice":
		doc_reference = "purchase_receipt"
		items_reference = "pr_detail"
		parent_doctype = "Purchase Receipt"
		child_doctype = "Purchase Receipt Item"
	else:
		doc_reference = "purchase_invoice"
		items_reference = "purchase_invoice_item"
		parent_doctype = "Purchase Invoice"
		child_doctype = "Purchase Invoice Item"

	purchase_receipts_or_invoices = []
	items = []

	for item in doc.get("items"):
		if item.get(doc_reference):
			purchase_receipts_or_invoices.append(item.get(doc_reference))
		if item.get(items_reference):
			items.append(item.get(items_reference))

	exchange_rate_map = frappe._dict(
		frappe.get_all(
			parent_doctype,
			filters={"name": ("in", purchase_receipts_or_invoices)},
			fields=["name", "conversion_rate"],
			as_list=1,
		)
	)

	net_rate_map = frappe._dict(
		frappe.get_all(child_doctype, filters={"name": ("in", items)}, fields=["name", "net_rate"], as_list=1)
	)

	return exchange_rate_map, net_rate_map


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Purchase Invoices"),
			"list_template": "templates/includes/list/list.html",
		}
	)
	return list_context


@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries


@frappe.whitelist()
def change_release_date(name: str, release_date: str | None = None):
	pi = frappe.get_lazy_doc("Purchase Invoice", name)
	pi.check_permission()
	pi.db_set("release_date", release_date)


@frappe.whitelist()
def unblock_invoice(name: str):
	if frappe.db.exists("Purchase Invoice", name):
		pi = frappe.get_lazy_doc("Purchase Invoice", name)
		pi.unblock_invoice()


@frappe.whitelist()
def block_invoice(name: str, release_date: str, hold_comment: str | None = None):
	if frappe.db.exists("Purchase Invoice", name):
		pi = frappe.get_lazy_doc("Purchase Invoice", name)
		pi.block_invoice(hold_comment, release_date)
