# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.document import Document
from frappe.utils import cint

from erpnext.accounts.utils import sync_auto_reconcile_config


class AccountsSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_taxes_from_item_tax_template: DF.Check
		add_taxes_from_taxes_and_charges_template: DF.Check
		allow_multi_currency_invoices_against_single_party_account: DF.Check
		allow_pegged_currencies_exchange_rates: DF.Check
		allow_stale: DF.Check
		auto_reconcile_payments: DF.Check
		auto_reconciliation_job_trigger: DF.Int
		automatically_fetch_payment_terms: DF.Check
		automatically_process_deferred_accounting_entry: DF.Check
		book_asset_depreciation_entry_automatically: DF.Check
		book_deferred_entries_based_on: DF.Literal["Days", "Months"]
		book_deferred_entries_via_journal_entry: DF.Check
		book_tax_discount_loss: DF.Check
		calculate_depr_using_total_days: DF.Check
		check_supplier_invoice_uniqueness: DF.Check
		confirm_before_resetting_posting_date: DF.Check
		create_pr_in_draft_status: DF.Check
		credit_controller: DF.Link | None
		delete_linked_ledger_entries: DF.Check
		determine_address_tax_category_from: DF.Literal["Billing Address", "Shipping Address"]
		enable_common_party_accounting: DF.Check
		enable_fuzzy_matching: DF.Check
		enable_immutable_ledger: DF.Check
		enable_party_matching: DF.Check
		exchange_gain_loss_posting_date: DF.Literal["Invoice", "Payment", "Reconciliation Date"]
		fetch_valuation_rate_for_internal_transaction: DF.Check
		general_ledger_remarks_length: DF.Int
		ignore_account_closing_balance: DF.Check
		ignore_is_opening_check_for_reporting: DF.Check
		maintain_same_internal_transaction_rate: DF.Check
		maintain_same_rate_action: DF.Literal["Stop", "Warn"]
		make_payment_via_journal_entry: DF.Check
		merge_similar_account_heads: DF.Check
		over_billing_allowance: DF.Currency
		post_change_gl_entries: DF.Check
		receivable_payable_fetch_method: DF.Literal["Buffered Cursor", "UnBuffered Cursor", "Raw SQL"]
		receivable_payable_remarks_length: DF.Int
		reconciliation_queue_size: DF.Int
		role_allowed_to_over_bill: DF.Link | None
		role_to_notify_on_depreciation_failure: DF.Link | None
		role_to_override_stop_action: DF.Link | None
		round_row_wise_tax: DF.Check
		show_balance_in_coa: DF.Check
		show_inclusive_tax_in_print: DF.Check
		show_payment_schedule_in_print: DF.Check
		show_taxes_as_table_in_print: DF.Check
		stale_days: DF.Int
		submit_journal_entries: DF.Check
		unlink_advance_payment_on_cancelation_of_order: DF.Check
		unlink_payment_on_cancellation_of_invoice: DF.Check
		use_legacy_budget_controller: DF.Check
		use_legacy_controller_for_pcv: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_auto_tax_settings()
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

		if clear_cache:
			frappe.clear_cache()

		self.validate_and_sync_auto_reconcile_config()

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

	def validate_and_sync_auto_reconcile_config(self):
		if self.has_value_changed("auto_reconciliation_job_trigger"):
			if (
				cint(self.auto_reconciliation_job_trigger) > 0
				and cint(self.auto_reconciliation_job_trigger) < 60
			):
				sync_auto_reconcile_config(self.auto_reconciliation_job_trigger)
			else:
				frappe.throw(_("Cron Interval should be between 1 and 59 Min"))

		if self.has_value_changed("reconciliation_queue_size"):
			if cint(self.reconciliation_queue_size) < 5 or cint(self.reconciliation_queue_size) > 100:
				frappe.throw(_("Queue Size should be between 5 and 100"))

	def validate_auto_tax_settings(self):
		if self.add_taxes_from_item_tax_template and self.add_taxes_from_taxes_and_charges_template:
			frappe.throw(
				_("You cannot enable both the settings '{0}' and '{1}'.").format(
					frappe.bold(_(self.meta.get_label("add_taxes_from_item_tax_template"))),
					frappe.bold(_(self.meta.get_label("add_taxes_from_taxes_and_charges_template"))),
				),
				title=_("Auto Tax Settings Error"),
			)

	@frappe.whitelist()
	def drop_ar_sql_procedures(self):
		from erpnext.accounts.report.accounts_receivable.accounts_receivable import InitSQLProceduresForAR

		frappe.db.sql(f"drop function if exists {InitSQLProceduresForAR.genkey_function_name}")
		frappe.db.sql(f"drop procedure if exists {InitSQLProceduresForAR.init_procedure_name}")
		frappe.db.sql(f"drop procedure if exists {InitSQLProceduresForAR.allocate_procedure_name}")
