# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.document import Document
from frappe.utils import cint

from erpnext.stock.utils import check_pending_reposting


class AccountsSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		acc_frozen_upto: DF.Date | None
		add_taxes_from_item_tax_template: DF.Check
		allow_multi_currency_invoices_against_single_party_account: DF.Check
		allow_stale: DF.Check
		auto_reconcile_payments: DF.Check
		automatically_fetch_payment_terms: DF.Check
		automatically_process_deferred_accounting_entry: DF.Check
		book_asset_depreciation_entry_automatically: DF.Check
		book_deferred_entries_based_on: DF.Literal["Days", "Months"]
		book_deferred_entries_via_journal_entry: DF.Check
		book_tax_discount_loss: DF.Check
		check_supplier_invoice_uniqueness: DF.Check
		credit_controller: DF.Link | None
		delete_linked_ledger_entries: DF.Check
		determine_address_tax_category_from: DF.Literal["Billing Address", "Shipping Address"]
		enable_common_party_accounting: DF.Check
		enable_fuzzy_matching: DF.Check
		enable_immutable_ledger: DF.Check
		enable_party_matching: DF.Check
		frozen_accounts_modifier: DF.Link | None
		general_ledger_remarks_length: DF.Int
		ignore_account_closing_balance: DF.Check
		make_payment_via_journal_entry: DF.Check
		merge_similar_account_heads: DF.Check
		over_billing_allowance: DF.Currency
		post_change_gl_entries: DF.Check
		receivable_payable_remarks_length: DF.Int
		role_allowed_to_over_bill: DF.Link | None
		round_row_wise_tax: DF.Check
		show_balance_in_coa: DF.Check
		show_inclusive_tax_in_print: DF.Check
		show_payment_schedule_in_print: DF.Check
		show_taxes_as_table_in_print: DF.Check
		stale_days: DF.Int
		submit_journal_entries: DF.Check
		unlink_advance_payment_on_cancelation_of_order: DF.Check
		unlink_payment_on_cancellation_of_invoice: DF.Check
	# end: auto-generated types

	def validate(self):
		old_doc = self.get_doc_before_save()
		clear_cache = False

		if old_doc.add_taxes_from_item_tax_template != self.add_taxes_from_item_tax_template:
			frappe.db.set_default(
				"add_taxes_from_item_tax_template", self.get("add_taxes_from_item_tax_template", 0)
			)
			clear_cache = True

		if old_doc.enable_common_party_accounting != self.enable_common_party_accounting:
			frappe.db.set_default(
				"enable_common_party_accounting", self.get("enable_common_party_accounting", 0)
			)
			clear_cache = True

		self.validate_stale_days()

		if old_doc.show_payment_schedule_in_print != self.show_payment_schedule_in_print:
			self.enable_payment_schedule_in_print()

		if old_doc.acc_frozen_upto != self.acc_frozen_upto:
			self.validate_pending_reposts()

		if clear_cache:
			frappe.clear_cache()

	def validate_stale_days(self):
		if not self.allow_stale and cint(self.stale_days) <= 0:
			frappe.msgprint(
				_("Stale Days should start from 1."), title="Error", indicator="red", raise_exception=1
			)

	def enable_payment_schedule_in_print(self):
		show_in_print = cint(self.show_payment_schedule_in_print)
		for doctype in ("Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice"):
			make_property_setter(
				doctype, "due_date", "print_hide", show_in_print, "Check", validate_fields_for_doctype=False
			)
			make_property_setter(
				doctype,
				"payment_schedule",
				"print_hide",
				0 if show_in_print else 1,
				"Check",
				validate_fields_for_doctype=False,
			)

	def validate_pending_reposts(self):
		if self.acc_frozen_upto:
			check_pending_reposting(self.acc_frozen_upto)
