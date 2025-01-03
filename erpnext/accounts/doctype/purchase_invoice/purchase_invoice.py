# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, qb, throw
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, cstr, flt, formatdate, get_link_to_form, getdate, nowdate

import erpnext
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
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
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.general_ledger import (
	get_round_off_account_and_cost_center,
	make_gl_entries,
	make_reverse_gl_entries,
	merge_similar_entries,
)
from erpnext.accounts.party import get_due_date, get_party_account
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from erpnext.assets.doctype.asset.asset import is_cwip_accounting_enabled
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.buying.utils import check_on_hold_or_closed_status
from erpnext.controllers.accounts_controller import validate_account_head
from erpnext.controllers.buying_controller import BuyingController
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	get_item_account_wise_additional_cost,
	update_billed_amount_based_on_po,
)


class WarehouseMissingError(frappe.ValidationError):
	pass


form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class PurchaseInvoice(BuyingController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.advance_tax.advance_tax import AdvanceTax
		from erpnext.accounts.doctype.payment_schedule.payment_schedule import PaymentSchedule
		from erpnext.accounts.doctype.pricing_rule_detail.pricing_rule_detail import PricingRuleDetail
		from erpnext.accounts.doctype.purchase_invoice_advance.purchase_invoice_advance import (
			PurchaseInvoiceAdvance,
		)
		from erpnext.accounts.doctype.purchase_invoice_item.purchase_invoice_item import PurchaseInvoiceItem
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import (
			PurchaseTaxesandCharges,
		)
		from erpnext.accounts.doctype.tax_withheld_vouchers.tax_withheld_vouchers import TaxWithheldVouchers
		from erpnext.buying.doctype.purchase_receipt_item_supplied.purchase_receipt_item_supplied import (
			PurchaseReceiptItemSupplied,
		)

		additional_discount_percentage: DF.Float
		address_display: DF.SmallText | None
		advance_tax: DF.Table[AdvanceTax]
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
		base_tax_withholding_net_total: DF.Currency
		base_taxes_and_charges_added: DF.Currency
		base_taxes_and_charges_deducted: DF.Currency
		base_total: DF.Currency
		base_total_taxes_and_charges: DF.Currency
		base_write_off_amount: DF.Currency
		bill_date: DF.Date | None
		bill_no: DF.Data | None
		billing_address: DF.Link | None
		billing_address_display: DF.SmallText | None
		buying_price_list: DF.Link | None
		cash_bank_account: DF.Link | None
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
		due_date: DF.Date | None
		from_date: DF.Date | None
		grand_total: DF.Currency
		group_same_items: DF.Check
		hold_comment: DF.SmallText | None
		ignore_default_payment_terms_template: DF.Check
		ignore_pricing_rule: DF.Check
		in_words: DF.Data | None
		incoterm: DF.Link | None
		inter_company_invoice_reference: DF.Link | None
		is_internal_supplier: DF.Check
		is_old_subcontracting_flow: DF.Check
		is_opening: DF.Literal["No", "Yes"]
		is_paid: DF.Check
		is_return: DF.Check
		is_subcontracted: DF.Check
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
		set_from_warehouse: DF.Link | None
		set_posting_time: DF.Check
		set_warehouse: DF.Link | None
		shipping_address: DF.Link | None
		shipping_address_display: DF.SmallText | None
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
		supplier_name: DF.Data | None
		supplier_warehouse: DF.Link | None
		tax_category: DF.Link | None
		tax_id: DF.ReadOnly | None
		tax_withheld_vouchers: DF.Table[TaxWithheldVouchers]
		tax_withholding_category: DF.Link | None
		tax_withholding_net_total: DF.Currency
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
		supplier_tds = frappe.db.get_value("Supplier", self.supplier, "tax_withholding_category")
		self.set_onload("supplier_tds", supplier_tds)

		if self.is_new():
			self.set("tax_withheld_vouchers", [])

	def before_save(self):
		if not self.on_hold:
			self.release_date = ""

	def invoice_is_blocked(self):
		return self.on_hold and (not self.release_date or self.release_date > getdate(nowdate()))

	def validate(self):
		if not self.is_opening:
			self.is_opening = "No"

		self.validate_posting_time()

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
		self.check_on_hold_or_closed_status()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.set_expense_account(for_validate=True)
		self.validate_expense_account()
		self.set_against_expense_account()
		self.validate_write_off_account()
		self.validate_multiple_billing("Purchase Receipt", "pr_detail", "amount")
		self.set_status()
		self.validate_purchase_receipt_if_update_stock()
		validate_inter_company_party(
			self.doctype, self.supplier, self.company, self.inter_company_invoice_reference
		)
		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.reset_default_field_value("set_from_warehouse", "items", "from_warehouse")
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

			else:
				self.remarks = _("No Remarks")

	def set_missing_values(self, for_validate=False):
		if not self.credit_to:
			self.credit_to = get_party_account("Supplier", self.supplier, self.company)
			self.party_account_currency = frappe.get_cached_value(
				"Account", self.credit_to, "account_currency"
			)
		if not self.due_date:
			self.due_date = get_due_date(
				self.posting_date, "Supplier", self.supplier, self.company, self.bill_date
			)

		tds_category = frappe.db.get_value("Supplier", self.supplier, "tax_withholding_category")
		if tds_category and not for_validate:
			self.apply_tds = 1
			self.tax_withholding_category = tds_category
			self.set_onload("supplier_tds", tds_category)

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

	def check_on_hold_or_closed_status(self):
		check_list = []

		for d in self.get("items"):
			if d.purchase_order and d.purchase_order not in check_list and not d.purchase_receipt:
				check_list.append(d.purchase_order)
				check_on_hold_or_closed_status("Purchase Order", d.purchase_order)

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
		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)

		if auto_accounting_for_stock:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")
			stock_items = self.get_stock_items()

		self.asset_received_but_not_billed = None

		if self.update_stock:
			self.validate_item_code()
			self.validate_warehouse(for_validate)
			if auto_accounting_for_stock:
				warehouse_account = get_warehouse_account_map(self.company)

		for item in self.get("items"):
			# in case of auto inventory accounting,
			# expense account is always "Stock Received But Not Billed" for a stock item
			# except opening entry, drop-ship entry and fixed asset items
			if (
				auto_accounting_for_stock
				and item.item_code in stock_items
				and self.is_opening == "No"
				and not item.is_fixed_asset
				and (
					not item.po_detail
					or not frappe.db.get_value("Purchase Order Item", item.po_detail, "delivered_by_supplier")
				)
			):
				if self.update_stock and item.warehouse and (not item.from_warehouse):
					if (
						for_validate
						and item.expense_account
						and item.expense_account != warehouse_account[item.warehouse]["account"]
					):
						msg = _(
							"Row {0}: Expense Head changed to {1} because account {2} is not linked to warehouse {3} or it is not the default inventory account"
						).format(
							item.idx,
							frappe.bold(warehouse_account[item.warehouse]["account"]),
							frappe.bold(item.expense_account),
							frappe.bold(item.warehouse),
						)
						frappe.msgprint(msg, title=_("Expense Head Changed"))
					item.expense_account = warehouse_account[item.warehouse]["account"]
				else:
					# check if 'Stock Received But Not Billed' account is credited in Purchase receipt or not
					if item.purchase_receipt:
						negative_expense_booked_in_pr = frappe.db.sql(
							"""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account = %s""",
							(item.purchase_receipt, stock_not_billed_account),
						)

						if negative_expense_booked_in_pr:
							if (
								for_validate
								and item.expense_account
								and item.expense_account != stock_not_billed_account
							):
								msg = _(
									"Row {0}: Expense Head changed to {1} because expense is booked against this account in Purchase Receipt {2}"
								).format(
									item.idx,
									frappe.bold(stock_not_billed_account),
									frappe.bold(item.purchase_receipt),
								)
								frappe.msgprint(msg, title=_("Expense Head Changed"))

							item.expense_account = stock_not_billed_account
					else:
						# If no purchase receipt present then book expense in 'Stock Received But Not Billed'
						# This is done in cases when Purchase Invoice is created before Purchase Receipt
						if (
							for_validate
							and item.expense_account
							and item.expense_account != stock_not_billed_account
						):
							msg = _(
								"Row {0}: Expense Head changed to {1} as no Purchase Receipt is created against Item {2}."
							).format(
								item.idx, frappe.bold(stock_not_billed_account), frappe.bold(item.item_code)
							)
							msg += "<br>"
							msg += _(
								"This is done to handle accounting for cases when Purchase Receipt is created after Purchase Invoice"
							)
							frappe.msgprint(msg, title=_("Expense Head Changed"))

						item.expense_account = stock_not_billed_account
			elif item.is_fixed_asset:
				account = None
				if not item.pr_detail and item.po_detail:
					receipt_item = frappe.get_cached_value(
						"Purchase Receipt Item",
						{
							"purchase_order": item.purchase_order,
							"purchase_order_item": item.po_detail,
							"docstatus": 1,
						},
						["name", "parent"],
						as_dict=1,
					)
					if receipt_item:
						item.pr_detail = receipt_item.name
						item.purchase_receipt = receipt_item.parent

				if item.pr_detail:
					if not self.asset_received_but_not_billed:
						self.asset_received_but_not_billed = self.get_company_default(
							"asset_received_but_not_billed"
						)

					# check if 'Asset Received But Not Billed' account is credited in Purchase receipt or not
					arbnb_booked_in_pr = frappe.db.get_value(
						"GL Entry",
						{
							"voucher_type": "Purchase Receipt",
							"voucher_no": item.purchase_receipt,
							"account": self.asset_received_but_not_billed,
						},
						"name",
					)
					if arbnb_booked_in_pr:
						account = self.asset_received_but_not_billed

				if not account:
					account_type = (
						"capital_work_in_progress_account"
						if is_cwip_accounting_enabled(item.asset_category)
						else "fixed_asset_account"
					)
					account = get_asset_category_account(
						account_type, item=item.item_code, company=self.company
					)
					if not account:
						form_link = get_link_to_form("Asset Category", item.asset_category)
						throw(
							_("Please set Fixed Asset Account in {} against {}.").format(
								form_link, self.company
							),
							title=_("Missing Account"),
						)
				item.expense_account = account
			elif not item.expense_account and for_validate:
				throw(_("Expense account is mandatory for item {0}").format(item.item_code or item.item_name))

	def validate_expense_account(self):
		for item in self.get("items"):
			validate_account_head(item.idx, item.expense_account, self.company, "Expense")

	def set_against_expense_account(self, force=False):
		against_accounts = []
		for item in self.get("items"):
			if item.expense_account and (item.expense_account not in against_accounts):
				against_accounts.append(item.expense_account)

		self.against_expense_account = ",".join(against_accounts)

	def force_set_against_expense_account(self):
		self.set_against_expense_account()
		frappe.db.set_value(self.doctype, self.name, "against_expense_account", self.against_expense_account)

	def po_required(self):
		if frappe.db.get_value("Buying Settings", None, "po_required") == "Yes":
			if frappe.get_value(
				"Supplier", self.supplier, "allow_purchase_invoice_creation_without_purchase_order"
			):
				return

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
		stock_items = self.get_stock_items()
		if frappe.db.get_value("Buying Settings", None, "pr_required") == "Yes":
			if frappe.get_value(
				"Supplier", self.supplier, "allow_purchase_invoice_creation_without_purchase_receipt"
			):
				return

			for d in self.get("items"):
				if not d.purchase_receipt and d.item_code in stock_items:
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
						_("Stock cannot be updated against Purchase Receipt {0}").format(
							item.purchase_receipt
						)
					)

	def validate_for_repost(self):
		self.validate_write_off_account()
		self.validate_expense_account()
		validate_docs_for_voucher_types(["Purchase Invoice"])
		validate_docs_for_deferred_accounting([], [self.name])

	def before_submit(self):
		self.create_remarks()

	def on_submit(self):
		super().on_submit()

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_purchase_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total
		)

		if not self.is_return:
			self.update_against_document_in_jv()
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.make_bundle_for_sales_purchase_return()
			self.make_bundle_using_old_serial_batch_fields()
			self.update_stock_ledger()

			if self.is_old_subcontracting_flow:
				self.set_consumed_qty_in_subcontract_order()

		# this sequence because outstanding may get -negative
		self.make_gl_entries()

		if self.update_stock == 1:
			self.repost_future_sle_and_gle()

		if frappe.db.get_single_value("Buying Settings", "project_update_frequency") == "Each Transaction":
			self.update_project()

		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)
		self.update_advance_tax_references()

		self.process_common_party_accounting()

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
			self.cancel_provisional_entries()

		self.update_supplier_outstanding(update_outstanding)

	def cancel_provisional_entries(self):
		rows = set()
		purchase_receipts = set()
		for d in self.items:
			if d.purchase_receipt:
				purchase_receipts.add(d.purchase_receipt)
				rows.add(d.name)

		if rows:
			# cancel gl entries
			gle = qb.DocType("GL Entry")
			gle_update_query = (
				qb.update(gle)
				.set(gle.is_cancelled, 1)
				.where(
					(gle.voucher_type == "Purchase Receipt")
					& (gle.voucher_no.isin(purchase_receipts))
					& (gle.voucher_detail_no.isin(rows))
				)
			)
			gle_update_query.run()

	def update_supplier_outstanding(self, update_outstanding):
		if update_outstanding == "No":
			update_outstanding_amt(
				self.credit_to,
				"Supplier",
				self.supplier,
				self.doctype,
				self.return_against if cint(self.is_return) and self.return_against else self.name,
			)

	def get_gl_entries(self, warehouse_account=None):
		self.auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)

		if self.auto_accounting_for_stock:
			self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
		else:
			self.stock_received_but_not_billed = None

		self.negative_expense_to_be_booked = 0.0
		gl_entries = []

		self.make_supplier_gl_entry(gl_entries)
		self.make_item_gl_entries(gl_entries)
		self.make_precision_loss_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)
		self.make_internal_transfer_gl_entries(gl_entries)
		self.make_gl_entries_for_tax_withholding(gl_entries)

		gl_entries = make_regional_gl_entries(gl_entries, self)

		gl_entries = merge_similar_entries(gl_entries)

		self.make_payment_gl_entries(gl_entries)
		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)
		return gl_entries

	def check_asset_cwip_enabled(self):
		# Check if there exists any item with cwip accounting enabled in it's asset category
		for item in self.get("items"):
			if item.item_code and item.is_fixed_asset:
				asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")
				if is_cwip_accounting_enabled(asset_category):
					return 1
		return 0

	def make_supplier_gl_entry(self, gl_entries):
		# Checked both rounding_adjustment and rounded_total
		# because rounded_total had value even before introduction of posting GLE based on rounded total
		grand_total = (
			self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
		)
		base_grand_total = flt(
			self.base_rounded_total
			if (self.base_rounding_adjustment and self.base_rounded_total)
			else self.base_grand_total,
			self.precision("base_grand_total"),
		)

		if grand_total and not self.is_internal_transfer():
			self.add_supplier_gl_entry(gl_entries, base_grand_total, grand_total)

	def add_supplier_gl_entry(
		self, gl_entries, base_grand_total, grand_total, against_account=None, remarks=None, skip_merge=False
	):
		against_voucher = self.name
		if self.is_return and self.return_against and not self.update_outstanding_for_self:
			against_voucher = self.return_against

		# Did not use base_grand_total to book rounding loss gle
		gl = {
			"account": self.credit_to,
			"party_type": "Supplier",
			"party": self.supplier,
			"due_date": self.due_date,
			"against": against_account or self.against_expense_account,
			"credit": base_grand_total,
			"credit_in_account_currency": base_grand_total
			if self.party_account_currency == self.company_currency
			else grand_total,
			"against_voucher": against_voucher,
			"against_voucher_type": self.doctype,
			"project": self.project,
			"cost_center": self.cost_center,
			"_skip_merge": skip_merge,
		}

		if remarks:
			gl["remarks"] = remarks

		gl_entries.append(self.get_gl_dict(gl, self.party_account_currency, item=self))

	def make_item_gl_entries(self, gl_entries):
		# item gl entries
		stock_items = self.get_stock_items()
		if self.update_stock and self.auto_accounting_for_stock:
			warehouse_account = get_warehouse_account_map(self.company)

		landed_cost_entries = get_item_account_wise_additional_cost(self.name)

		voucher_wise_stock_value = {}
		if self.update_stock:
			stock_ledger_entries = frappe.get_all(
				"Stock Ledger Entry",
				fields=["voucher_detail_no", "stock_value_difference", "warehouse"],
				filters={"voucher_no": self.name, "voucher_type": self.doctype, "is_cancelled": 0},
			)
			for d in stock_ledger_entries:
				voucher_wise_stock_value.setdefault(
					(d.voucher_detail_no, d.warehouse), d.stock_value_difference
				)

		valuation_tax_accounts = [
			d.account_head
			for d in self.get("taxes")
			if d.category in ("Valuation", "Total and Valuation")
			and flt(d.base_tax_amount_after_discount_amount)
		]

		exchange_rate_map, net_rate_map = get_purchase_document_details(self)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)
		if provisional_accounting_for_non_stock_items:
			self.get_provisional_accounts()

		for item in self.get("items"):
			if flt(item.base_net_amount):
				account_currency = get_account_currency(item.expense_account)
				if item.item_code:
					frappe.get_cached_value("Item", item.item_code, "asset_category")

				if (
					self.update_stock
					and self.auto_accounting_for_stock
					and (item.item_code in stock_items or item.is_fixed_asset)
				):
					# warehouse account
					warehouse_debit_amount = self.make_stock_adjustment_entry(
						gl_entries, item, voucher_wise_stock_value, account_currency
					)

					if item.from_warehouse:
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": warehouse_account[item.warehouse]["account"],
									"against": warehouse_account[item.from_warehouse]["account"],
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": warehouse_debit_amount,
								},
								warehouse_account[item.warehouse]["account_currency"],
								item=item,
							)
						)

						credit_amount = item.base_net_amount
						if self.is_internal_supplier and item.valuation_rate:
							credit_amount = flt(item.valuation_rate * item.stock_qty)

						# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": warehouse_account[item.from_warehouse]["account"],
									"against": warehouse_account[item.warehouse]["account"],
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": -1 * flt(credit_amount, item.precision("base_net_amount")),
								},
								warehouse_account[item.from_warehouse]["account_currency"],
								item=item,
							)
						)

						# Do not book expense for transfer within same company transfer
						if not self.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": self.supplier,
										"debit": flt(item.base_net_amount, item.precision("base_net_amount")),
										"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project,
									},
									account_currency,
									item=item,
								)
							)

					else:
						if not self.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": self.supplier,
										"debit": warehouse_debit_amount,
										"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project or self.project,
									},
									account_currency,
									item=item,
								)
							)

					# Amount added through landed-cost-voucher
					if landed_cost_entries:
						if (item.item_code, item.name) in landed_cost_entries:
							for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": account,
											"against": item.expense_account,
											"cost_center": item.cost_center,
											"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
											"credit": flt(amount["base_amount"]),
											"credit_in_account_currency": flt(amount["amount"]),
											"project": item.project or self.project,
										},
										item=item,
									)
								)

					# sub-contracting warehouse
					if flt(item.rm_supp_cost):
						supplier_warehouse_account = warehouse_account[self.supplier_warehouse]["account"]
						if not supplier_warehouse_account:
							frappe.throw(
								_("Please set account in Warehouse {0}").format(self.supplier_warehouse)
							)
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": supplier_warehouse_account,
									"against": item.expense_account,
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"credit": flt(item.rm_supp_cost),
								},
								warehouse_account[self.supplier_warehouse]["account_currency"],
								item=item,
							)
						)

				else:
					expense_account = (
						item.expense_account
						if (not item.enable_deferred_expense or self.is_return)
						else item.deferred_expense_account
					)

					dummy, amount = self.get_amount_and_base_amount(item, None)

					if provisional_accounting_for_non_stock_items:
						self.make_provisional_gl_entry(gl_entries, item)

					if not self.is_internal_transfer():
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": expense_account,
									"against": self.supplier,
									"debit": amount,
									"cost_center": item.cost_center,
									"project": item.project or self.project,
								},
								account_currency,
								item=item,
							)
						)

						# check if the exchange rate has changed
						if item.get("purchase_receipt") and self.auto_accounting_for_stock:
							if (
								exchange_rate_map[item.purchase_receipt]
								and self.conversion_rate != exchange_rate_map[item.purchase_receipt]
								and item.net_rate == net_rate_map[item.pr_detail]
							):
								discrepancy_caused_by_exchange_rate_difference = (
									item.qty * item.net_rate
								) * (exchange_rate_map[item.purchase_receipt] - self.conversion_rate)

								gl_entries.append(
									self.get_gl_dict(
										{
											"account": expense_account,
											"against": self.supplier,
											"debit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or self.project,
										},
										account_currency,
										item=item,
									)
								)
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": self.get_company_default("exchange_gain_loss_account"),
											"against": self.supplier,
											"credit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or self.project,
										},
										account_currency,
										item=item,
									)
								)
			if (
				self.auto_accounting_for_stock
				and self.is_opening == "No"
				and item.item_code in stock_items
				and item.item_tax_amount
			):
				# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
				if item.purchase_receipt and valuation_tax_accounts:
					negative_expense_booked_in_pr = frappe.db.sql(
						"""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account in %s""",
						(item.purchase_receipt, valuation_tax_accounts),
					)

					stock_rbnb = (
						self.get_company_default("asset_received_but_not_billed")
						if item.is_fixed_asset
						else self.stock_received_but_not_billed
					)

					if not negative_expense_booked_in_pr:
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": stock_rbnb,
									"against": self.supplier,
									"debit": flt(item.item_tax_amount, item.precision("item_tax_amount")),
									"remarks": self.remarks or _("Accounting Entry for Stock"),
									"cost_center": self.cost_center,
									"project": item.project or self.project,
								},
								item=item,
							)
						)

						self.negative_expense_to_be_booked += flt(
							item.item_tax_amount, item.precision("item_tax_amount")
						)

			if item.is_fixed_asset and item.landed_cost_voucher_amount:
				self.update_gross_purchase_amount_for_linked_assets(item)

	def get_provisional_accounts(self):
		self.provisional_accounts = frappe._dict()
		linked_purchase_receipts = set([d.purchase_receipt for d in self.items if d.purchase_receipt])
		pr_items = frappe.get_all(
			"Purchase Receipt Item",
			filters={"parent": ("in", linked_purchase_receipts)},
			fields=["name", "provisional_expense_account", "qty", "base_rate"],
		)
		default_provisional_account = self.get_company_default("default_provisional_account")
		provisional_accounts = set(
			[
				d.provisional_expense_account
				if d.provisional_expense_account
				else default_provisional_account
				for d in pr_items
			]
		)

		provisional_gl_entries = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Purchase Receipt",
				"voucher_no": ("in", linked_purchase_receipts),
				"account": ("in", provisional_accounts),
				"is_cancelled": 0,
			},
			fields=["voucher_detail_no"],
		)
		rows_with_provisional_entries = [d.voucher_detail_no for d in provisional_gl_entries]
		for item in pr_items:
			self.provisional_accounts[item.name] = {
				"provisional_account": item.provisional_expense_account or default_provisional_account,
				"qty": item.qty,
				"base_rate": item.base_rate,
				"has_provisional_entry": item.name in rows_with_provisional_entries,
			}

	def make_provisional_gl_entry(self, gl_entries, item):
		if item.purchase_receipt:
			pr_item = self.provisional_accounts.get(item.pr_detail, {})
			if pr_item.get("has_provisional_entry"):
				purchase_receipt_doc = frappe.get_cached_doc("Purchase Receipt", item.purchase_receipt)

				# Intentionally passing purchase invoice item to handle partial billing
				purchase_receipt_doc.add_provisional_gl_entry(
					item,
					gl_entries,
					self.posting_date,
					pr_item.get("provisional_account"),
					reverse=1,
					item_amount=(min(item.qty, pr_item.get("qty")) * pr_item.get("base_rate")),
				)

	def update_gross_purchase_amount_for_linked_assets(self, item):
		assets = frappe.db.get_all(
			"Asset",
			filters={
				"purchase_invoice": self.name,
				"item_code": item.item_code,
				"purchase_invoice_item": ("in", [item.name, ""]),
			},
			fields=["name", "asset_quantity"],
		)
		for asset in assets:
			purchase_amount = flt(item.valuation_rate) * asset.asset_quantity
			frappe.db.set_value(
				"Asset",
				asset.name,
				{
					"gross_purchase_amount": purchase_amount,
					"purchase_amount": purchase_amount,
				},
			)

	def make_stock_adjustment_entry(self, gl_entries, item, voucher_wise_stock_value, account_currency):
		net_amt_precision = item.precision("base_net_amount")
		val_rate_db_precision = 6 if cint(item.precision("valuation_rate")) <= 6 else 9

		warehouse_debit_amount = flt(
			flt(item.valuation_rate, val_rate_db_precision) * flt(item.qty) * flt(item.conversion_factor),
			net_amt_precision,
		)

		# Stock ledger value is not matching with the warehouse amount
		if (
			self.update_stock
			and voucher_wise_stock_value.get((item.name, item.warehouse))
			and warehouse_debit_amount
			!= flt(voucher_wise_stock_value.get((item.name, item.warehouse)), net_amt_precision)
		):
			cost_of_goods_sold_account = self.get_company_default("default_expense_account")
			stock_amount = flt(voucher_wise_stock_value.get((item.name, item.warehouse)), net_amt_precision)
			stock_adjustment_amt = warehouse_debit_amount - stock_amount

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": cost_of_goods_sold_account,
						"against": item.expense_account,
						"debit": stock_adjustment_amt,
						"remarks": self.get("remarks") or _("Stock Adjustment"),
						"cost_center": item.cost_center,
						"project": item.project or self.project,
					},
					account_currency,
					item=item,
				)
			)

			warehouse_debit_amount = stock_amount

		return warehouse_debit_amount

	def make_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		valuation_tax = {}

		for tax in self.get("taxes"):
			amount, base_amount = self.get_tax_amounts(tax, None)
			if tax.category in ("Total", "Valuation and Total") and flt(base_amount):
				account_currency = get_account_currency(tax.account_head)

				dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": tax.account_head,
							"against": self.supplier,
							dr_or_cr: base_amount,
							dr_or_cr + "_in_account_currency": base_amount
							if account_currency == self.company_currency
							else amount,
							"cost_center": tax.cost_center,
						},
						account_currency,
						item=tax,
					)
				)
			# accumulate valuation tax
			if (
				self.is_opening == "No"
				and tax.category in ("Valuation", "Valuation and Total")
				and flt(base_amount)
				and not self.is_internal_transfer()
			):
				if self.auto_accounting_for_stock and not tax.cost_center:
					frappe.throw(
						_("Cost Center is required in row {0} in Taxes table for type {1}").format(
							tax.idx, _(tax.category)
						)
					)
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(base_amount)

		if self.is_opening == "No" and self.negative_expense_to_be_booked and valuation_tax:
			# credit valuation tax amount in "Expenses Included In Valuation"
			# this will balance out valuation amount included in cost of goods sold

			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = self.negative_expense_to_be_booked
			i = 1
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = self.negative_expense_to_be_booked * (
							valuation_tax[tax.name] / total_valuation_amount
						)
						amount_including_divisional_loss -= applicable_amount

					gl_entries.append(
						self.get_gl_dict(
							{
								"account": tax.account_head,
								"cost_center": tax.cost_center,
								"against": self.supplier,
								"credit": applicable_amount,
								"remarks": self.remarks or _("Accounting Entry for Stock"),
							},
							item=tax,
						)
					)

					i += 1

		if self.auto_accounting_for_stock and self.update_stock and valuation_tax:
			for tax in self.get("taxes"):
				if valuation_tax.get(tax.name):
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": tax.account_head,
								"cost_center": tax.cost_center,
								"against": self.supplier,
								"credit": valuation_tax[tax.name],
								"remarks": self.remarks or _("Accounting Entry for Stock"),
							},
							item=tax,
						)
					)

	def make_internal_transfer_gl_entries(self, gl_entries):
		if self.is_internal_transfer() and flt(self.base_total_taxes_and_charges):
			account_currency = get_account_currency(self.unrealized_profit_loss_account)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.unrealized_profit_loss_account,
						"against": self.supplier,
						"credit": flt(self.total_taxes_and_charges),
						"credit_in_account_currency": flt(self.base_total_taxes_and_charges),
						"cost_center": self.cost_center,
					},
					account_currency,
					item=self,
				)
			)

	def make_gl_entries_for_tax_withholding(self, gl_entries):
		"""
		Tax withholding amount is not part of supplier invoice.
		Separate supplier GL Entry for correct reporting.
		"""
		if not self.apply_tds:
			return

		for row in self.get("taxes"):
			if not row.is_tax_withholding_account or not row.tax_amount:
				continue

			base_tds_amount = row.base_tax_amount_after_discount_amount
			tds_amount = row.tax_amount_after_discount_amount

			self.add_supplier_gl_entry(gl_entries, base_tds_amount, tds_amount)
			self.add_supplier_gl_entry(
				gl_entries,
				-base_tds_amount,
				-tds_amount,
				against_account=row.account_head,
				remarks=_("TDS Deducted"),
				skip_merge=True,
			)

	def make_payment_gl_entries(self, gl_entries):
		# Make Cash GL Entries
		if cint(self.is_paid) and self.cash_bank_account and self.paid_amount:
			bank_account_currency = get_account_currency(self.cash_bank_account)
			# CASH, make payment entries
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.credit_to,
						"party_type": "Supplier",
						"party": self.supplier,
						"against": self.cash_bank_account,
						"debit": self.base_paid_amount,
						"debit_in_account_currency": self.base_paid_amount
						if self.party_account_currency == self.company_currency
						else self.paid_amount,
						"against_voucher": self.return_against
						if cint(self.is_return) and self.return_against
						else self.name,
						"against_voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"project": self.project,
					},
					self.party_account_currency,
					item=self,
				)
			)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.cash_bank_account,
						"against": self.supplier,
						"credit": self.base_paid_amount,
						"credit_in_account_currency": self.base_paid_amount
						if bank_account_currency == self.company_currency
						else self.paid_amount,
						"cost_center": self.cost_center,
					},
					bank_account_currency,
					item=self,
				)
			)

	def make_write_off_gl_entry(self, gl_entries):
		# writeoff account includes petty difference in the invoice amount
		# and the amount that is paid
		if self.write_off_account and flt(self.write_off_amount):
			write_off_account_currency = get_account_currency(self.write_off_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.credit_to,
						"party_type": "Supplier",
						"party": self.supplier,
						"against": self.write_off_account,
						"debit": self.base_write_off_amount,
						"debit_in_account_currency": self.base_write_off_amount
						if self.party_account_currency == self.company_currency
						else self.write_off_amount,
						"against_voucher": self.return_against
						if cint(self.is_return) and self.return_against
						else self.name,
						"against_voucher_type": self.doctype,
						"cost_center": self.cost_center,
						"project": self.project,
					},
					self.party_account_currency,
					item=self,
				)
			)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.write_off_account,
						"against": self.supplier,
						"credit": flt(self.base_write_off_amount),
						"credit_in_account_currency": self.base_write_off_amount
						if write_off_account_currency == self.company_currency
						else self.write_off_amount,
						"cost_center": self.cost_center or self.write_off_cost_center,
					},
					item=self,
				)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		# if rounding adjustment in small and conversion rate is also small then
		# base_rounding_adjustment may become zero due to small precision
		# eg: rounding_adjustment = 0.01 and exchange rate = 0.05 and precision of base_rounding_adjustment is 2
		# 	then base_rounding_adjustment becomes zero and error is thrown in GL Entry
		if not self.is_internal_transfer() and self.rounding_adjustment and self.base_rounding_adjustment:
			(
				round_off_account,
				round_off_cost_center,
				round_off_for_opening,
			) = get_round_off_account_and_cost_center(
				self.company, "Purchase Invoice", self.name, self.use_company_roundoff_cost_center
			)

			if self.is_opening == "Yes" and self.rounding_adjustment:
				if not round_off_for_opening:
					frappe.throw(
						_(
							"Opening Invoice has rounding adjustment of {0}.<br><br> '{1}' account is required to post these values. Please set it in Company: {2}.<br><br> Or, '{3}' can be enabled to not post any rounding adjustment."
						).format(
							frappe.bold(self.rounding_adjustment),
							frappe.bold("Round Off for Opening"),
							get_link_to_form("Company", self.company),
							frappe.bold("Disable Rounded Total"),
						)
					)
				else:
					round_off_account = round_off_for_opening

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": round_off_account,
						"against": self.supplier,
						"debit_in_account_currency": self.rounding_adjustment,
						"debit": self.base_rounding_adjustment,
						"cost_center": round_off_cost_center
						if self.use_company_roundoff_cost_center
						else (self.cost_center or round_off_cost_center),
					},
					item=self,
				)
			)

	def on_cancel(self):
		check_if_return_invoice_linked_with_payment_entry(self)

		super().on_cancel()

		self.check_on_hold_or_closed_status()

		if self.is_return and not self.update_billed_amount_in_purchase_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Purchase Receipt")
			self.update_billing_status_for_zero_amount_refdoc("Purchase Order")

		self.update_billing_status_in_pr()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating ordered qty in bin depends upon updated ordered qty in PO
		if self.update_stock == 1:
			self.update_stock_ledger()
			self.delete_auto_created_batches()

			if self.is_old_subcontracting_flow:
				self.set_consumed_qty_in_subcontract_order()

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
			"Tax Withheld Vouchers",
			"Serial and Batch Bundle",
		)
		self.update_advance_tax_references(cancel=1)

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
			project_doc = frappe.get_doc("Project", proj)
			project_doc.total_purchase_cost = current_purchase_cost + value
			project_doc.calculate_gross_margin()
			project_doc.db_update()

	def validate_supplier_invoice(self):
		if self.bill_date:
			if getdate(self.bill_date) > getdate(self.posting_date):
				frappe.throw(_("Supplier Invoice Date cannot be greater than Posting Date"))

		if self.bill_no:
			if cint(frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness")):
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

	def update_billing_status_in_pr(self, update_modified=True):
		if self.is_return and not self.update_billed_amount_in_purchase_receipt:
			return

		updated_pr = []
		po_details = []

		pr_details_billed_amt = self.get_pr_details_billed_amt()

		for d in self.get("items"):
			if d.pr_detail:
				frappe.db.set_value(
					"Purchase Receipt Item",
					d.pr_detail,
					"billed_amt",
					flt(pr_details_billed_amt.get(d.pr_detail)),
					update_modified=update_modified,
				)
				updated_pr.append(d.purchase_receipt)
			elif d.po_detail:
				po_details.append(d.po_detail)

		if po_details:
			updated_pr += update_billed_amount_based_on_po(po_details, update_modified)

		adjust_incoming_rate = frappe.db.get_single_value(
			"Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate"
		)

		for pr in set(updated_pr):
			from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billing_percentage

			pr_doc = frappe.get_doc("Purchase Receipt", pr)
			update_billing_percentage(
				pr_doc, update_modified=update_modified, adjust_incoming_rate=adjust_incoming_rate
			)

	def get_pr_details_billed_amt(self):
		# Get billed amount based on purchase receipt item reference (pr_detail) in purchase invoice

		pr_details_billed_amt = {}
		pr_details = [d.get("pr_detail") for d in self.get("items") if d.get("pr_detail")]
		if pr_details:
			doctype = frappe.qb.DocType("Purchase Invoice Item")
			query = (
				frappe.qb.from_(doctype)
				.select(doctype.pr_detail, Sum(doctype.amount))
				.where(doctype.pr_detail.isin(pr_details) & doctype.docstatus == 1)
				.groupby(doctype.pr_detail)
			)

			pr_details_billed_amt = frappe._dict(query.run(as_list=1))

		return pr_details_billed_amt

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.due_date = None

	def block_invoice(self, hold_comment=None, release_date=None):
		self.db_set("on_hold", 1)
		self.db_set("hold_comment", cstr(hold_comment))
		self.db_set("release_date", release_date)

	def unblock_invoice(self):
		self.db_set("on_hold", 0)
		self.db_set("release_date", None)

	def set_tax_withholding(self):
		self.set("advance_tax", [])
		self.set("tax_withheld_vouchers", [])

		if not self.apply_tds:
			return

		if self.apply_tds and not self.get("tax_withholding_category"):
			self.tax_withholding_category = frappe.db.get_value(
				"Supplier", self.supplier, "tax_withholding_category"
			)

		if not self.tax_withholding_category:
			return

		tax_withholding_details, advance_taxes, voucher_wise_amount = get_party_tax_withholding_details(
			self, self.tax_withholding_category
		)

		# Adjust TDS paid on advances
		self.allocate_advance_tds(tax_withholding_details, advance_taxes)

		if not tax_withholding_details:
			return

		accounts = []
		for d in self.taxes:
			if d.account_head == tax_withholding_details.get("account_head"):
				d.update(tax_withholding_details)

			accounts.append(d.account_head)

		if not accounts or tax_withholding_details.get("account_head") not in accounts:
			self.append("taxes", tax_withholding_details)

		to_remove = [
			d
			for d in self.taxes
			if not d.tax_amount and d.account_head == tax_withholding_details.get("account_head")
		]

		for d in to_remove:
			self.remove(d)

		## Add pending vouchers on which tax was withheld
		for voucher_no, voucher_details in voucher_wise_amount.items():
			self.append(
				"tax_withheld_vouchers",
				{
					"voucher_name": voucher_no,
					"voucher_type": voucher_details.get("voucher_type"),
					"taxable_amount": voucher_details.get("amount"),
				},
			)

		# calculate totals again after applying TDS
		self.calculate_taxes_and_totals()

	def allocate_advance_tds(self, tax_withholding_details, advance_taxes):
		for tax in advance_taxes:
			allocated_amount = 0
			pending_amount = flt(tax.tax_amount - tax.allocated_amount)
			if flt(tax_withholding_details.get("tax_amount")) >= pending_amount:
				tax_withholding_details["tax_amount"] -= pending_amount
				allocated_amount = pending_amount
			elif (
				flt(tax_withholding_details.get("tax_amount"))
				and flt(tax_withholding_details.get("tax_amount")) < pending_amount
			):
				allocated_amount = tax_withholding_details["tax_amount"]
				tax_withholding_details["tax_amount"] = 0

			self.append(
				"advance_tax",
				{
					"reference_type": "Payment Entry",
					"reference_name": tax.parent,
					"reference_detail": tax.name,
					"account_head": tax.account_head,
					"allocated_amount": allocated_amount,
				},
			)

	def update_advance_tax_references(self, cancel=0):
		for tax in self.get("advance_tax"):
			at = frappe.qb.DocType("Advance Taxes and Charges").as_("at")

			if cancel:
				frappe.qb.update(at).set(
					at.allocated_amount, at.allocated_amount - tax.allocated_amount
				).where(at.name == tax.reference_detail).run()
			else:
				frappe.qb.update(at).set(
					at.allocated_amount, at.allocated_amount + tax.allocated_amount
				).where(at.name == tax.reference_detail).run()

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
		}
	)
	return list_context


@erpnext.allow_regional
def make_regional_gl_entries(gl_entries, doc):
	return gl_entries


@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Invoice", source_name, target_doc)


@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {"doctype": "Stock Entry", "validation": {"docstatus": ["=", 1]}},
			"Purchase Invoice Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {"stock_qty": "transfer_qty", "batch_no": "batch_no"},
			},
		},
		target_doc,
	)

	return doc


@frappe.whitelist()
def change_release_date(name, release_date=None):
	if frappe.db.exists("Purchase Invoice", name):
		pi = frappe.get_doc("Purchase Invoice", name)
		pi.db_set("release_date", release_date)


@frappe.whitelist()
def unblock_invoice(name):
	if frappe.db.exists("Purchase Invoice", name):
		pi = frappe.get_doc("Purchase Invoice", name)
		pi.unblock_invoice()


@frappe.whitelist()
def block_invoice(name, release_date, hold_comment=None):
	if frappe.db.exists("Purchase Invoice", name):
		pi = frappe.get_doc("Purchase Invoice", name)
		pi.block_invoice(hold_comment, release_date)


@frappe.whitelist()
def make_inter_company_sales_invoice(source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction

	return make_inter_company_transaction("Purchase Invoice", source_name, target_doc)


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.received_qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (
			(flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate) * flt(source_parent.conversion_rate)
		)

	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {
				"doctype": "Purchase Receipt",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Invoice Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_invoice_item",
					"parent": "purchase_invoice",
					"bom": "bom",
					"purchase_order": "purchase_order",
					"po_detail": "purchase_order_item",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty),
			},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges"},
		},
		target_doc,
	)

	return doc
