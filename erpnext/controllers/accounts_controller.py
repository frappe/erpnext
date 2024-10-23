# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import defaultdict

import frappe
from frappe import _, bold, qb, throw
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import (
	add_days,
	add_months,
	cint,
	comma_and,
	flt,
	fmt_money,
	formatdate,
	get_last_day,
	get_link_to_form,
	getdate,
	nowdate,
	parse_json,
	today,
)

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimensions,
)
from erpnext.accounts.doctype.pricing_rule.utils import (
	apply_pricing_rule_for_free_items,
	apply_pricing_rule_on_transaction,
	get_applied_pricing_rules,
)
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.party import (
	get_party_account,
	get_party_account_currency,
	get_party_gle_currency,
	validate_party_frozen_disabled,
)
from erpnext.accounts.utils import (
	create_gain_loss_journal,
	get_account_currency,
	get_currency_precision,
	get_fiscal_years,
	validate_fiscal_year,
)
from erpnext.buying.utils import update_last_purchase_rate
from erpnext.controllers.print_settings import (
	set_print_templates_for_item_table,
	set_print_templates_for_taxes,
)
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.exceptions import InvalidCurrency
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.get_item_details import (
	_get_item_tax_template,
	get_conversion_factor,
	get_item_details,
	get_item_tax_map,
	get_item_warehouse,
)
from erpnext.utilities.regional import temporary_flag
from erpnext.utilities.transaction_base import TransactionBase


class AccountMissingError(frappe.ValidationError):
	pass


class InvalidQtyError(frappe.ValidationError):
	pass


force_item_fields = (
	"item_group",
	"brand",
	"stock_uom",
	"is_fixed_asset",
	"pricing_rules",
	"weight_per_unit",
	"weight_uom",
	"total_weight",
	"valuation_rate",
)


class AccountsController(TransactionBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def get_print_settings(self):
		print_setting_fields = []
		items_field = self.meta.get_field("items")

		if items_field and items_field.fieldtype == "Table":
			print_setting_fields += ["compact_item_print", "print_uom_after_quantity"]

		taxes_field = self.meta.get_field("taxes")
		if taxes_field and taxes_field.fieldtype == "Table":
			print_setting_fields += ["print_taxes_with_zero_amount"]

		return print_setting_fields

	@property
	def company_currency(self):
		if not hasattr(self, "__company_currency"):
			self.__company_currency = erpnext.get_company_currency(self.company)

		return self.__company_currency

	def onload(self):
		self.set_onload(
			"make_payment_via_journal_entry",
			frappe.db.get_single_value("Accounts Settings", "make_payment_via_journal_entry"),
		)

		if self.is_new():
			relevant_docs = (
				"Quotation",
				"Purchase Order",
				"Sales Order",
				"Purchase Invoice",
				"Sales Invoice",
			)
			if self.doctype in relevant_docs:
				self.set_payment_schedule()

	def remove_bundle_for_non_stock_invoices(self):
		has_sabb = False
		if self.doctype in ("Sales Invoice", "Purchase Invoice") and not self.update_stock:
			for item in self.get("items"):
				if item.serial_and_batch_bundle:
					item.serial_and_batch_bundle = None
					has_sabb = True

		if has_sabb:
			self.remove_serial_and_batch_bundle()

	def ensure_supplier_is_not_blocked(self):
		is_supplier_payment = self.doctype == "Payment Entry" and self.party_type == "Supplier"
		is_buying_invoice = self.doctype in ["Purchase Invoice", "Purchase Order"]
		supplier = None
		supplier_name = None

		if is_buying_invoice or is_supplier_payment:
			supplier_name = self.supplier if is_buying_invoice else self.party
			supplier = frappe.get_doc("Supplier", supplier_name)

		if supplier and supplier_name and supplier.on_hold:
			if (is_buying_invoice and supplier.hold_type in ["All", "Invoices"]) or (
				is_supplier_payment and supplier.hold_type in ["All", "Payments"]
			):
				if not supplier.release_date or getdate(nowdate()) <= supplier.release_date:
					frappe.msgprint(
						_("{0} is blocked so this transaction cannot proceed").format(supplier_name),
						raise_exception=1,
					)

	def validate(self):
		if not self.get("is_return") and not self.get("is_debit_note"):
			self.validate_qty_is_not_zero()

		if (
			self.doctype in ["Sales Invoice", "Purchase Invoice"]
			and self.get("is_return")
			and self.get("update_stock")
		):
			self.validate_zero_qty_for_return_invoices_with_stock()

		if self.get("_action") and self._action != "update_after_submit":
			self.set_missing_values(for_validate=True)

		if self.get("_action") == "submit":
			self.remove_bundle_for_non_stock_invoices()

		self.ensure_supplier_is_not_blocked()

		self.validate_date_with_fiscal_year()
		self.validate_party_accounts()

		self.validate_inter_company_reference()

		self.disable_pricing_rule_on_internal_transfer()
		self.disable_tax_included_prices_for_internal_transfer()
		self.set_incoming_rate()
		self.init_internal_values()

		if self.meta.get_field("currency"):
			self.calculate_taxes_and_totals()

			if not self.meta.get_field("is_return") or not self.is_return:
				self.validate_value("base_grand_total", ">=", 0)

			validate_return(self)

		self.validate_all_documents_schedule()

		if self.meta.get_field("taxes_and_charges"):
			self.validate_enabled_taxes_and_charges()
			self.validate_tax_account_company()

		self.validate_party()
		self.validate_currency()
		self.validate_party_account_currency()
		self.validate_return_against_account()

		if self.doctype in ["Purchase Invoice", "Sales Invoice"]:
			if invalid_advances := [x for x in self.advances if not x.reference_type or not x.reference_name]:
				frappe.throw(
					_(
						"Rows: {0} in {1} section are Invalid. Reference Name should point to a valid Payment Entry or Journal Entry."
					).format(
						frappe.bold(comma_and([x.idx for x in invalid_advances])),
						frappe.bold(_("Advance Payments")),
					)
				)

			if self.get("is_return") and self.get("return_against") and not self.get("is_pos"):
				if self.get("update_outstanding_for_self"):
					document_type = "Credit Note" if self.doctype == "Sales Invoice" else "Debit Note"
					frappe.msgprint(
						_(
							"We can see {0} is made against {1}. If you want {1}'s outstanding to be updated, uncheck '{2}' checkbox. <br><br> Or you can use {3} tool to reconcile against {1} later."
						).format(
							frappe.bold(document_type),
							get_link_to_form(self.doctype, self.get("return_against")),
							frappe.bold(_("Update Outstanding for Self")),
							get_link_to_form("Payment Reconciliation", "Payment Reconciliation"),
						)
					)

			pos_check_field = "is_pos" if self.doctype == "Sales Invoice" else "is_paid"
			if cint(self.allocate_advances_automatically) and not cint(self.get(pos_check_field)):
				self.set_advances()

			self.set_advance_gain_or_loss()

			if self.is_return:
				self.validate_qty()
			else:
				self.validate_deferred_start_and_end_date()

			self.validate_deferred_income_expense_account()
			self.set_inter_company_account()

		if self.doctype == "Purchase Invoice":
			self.calculate_paid_amount()
			# apply tax withholding only if checked and applicable
			self.set_tax_withholding()

		with temporary_flag("company", self.company):
			validate_regional(self)
			validate_einvoice_fields(self)

		if self.doctype != "Material Request" and not self.ignore_pricing_rule:
			apply_pricing_rule_on_transaction(self)

		self.set_total_in_words()
		self.set_default_letter_head()

	def set_default_letter_head(self):
		if hasattr(self, "letter_head") and not self.letter_head:
			self.letter_head = frappe.db.get_value("Company", self.company, "default_letter_head")

	def init_internal_values(self):
		# init all the internal values as 0 on sa
		if self.docstatus.is_draft():
			# TODO: Add all such pending values here
			fields = ["billed_amt", "delivered_qty"]
			for item in self.get("items"):
				for field in fields:
					if hasattr(item, field):
						item.set(field, 0)

	def before_cancel(self):
		validate_einvoice_fields(self)

	def _remove_references_in_unreconcile(self):
		upe = frappe.qb.DocType("Unreconcile Payment Entries")
		rows = (
			frappe.qb.from_(upe)
			.select(upe.name, upe.parent)
			.where((upe.reference_doctype == self.doctype) & (upe.reference_name == self.name))
			.run(as_dict=True)
		)

		if rows:
			references_map = frappe._dict()
			for x in rows:
				references_map.setdefault(x.parent, []).append(x.name)

			for doc, rows in references_map.items():
				unreconcile_doc = frappe.get_doc("Unreconcile Payment", doc)
				for row in rows:
					unreconcile_doc.remove(unreconcile_doc.get("allocations", {"name": row})[0])

				unreconcile_doc.flags.ignore_validate_update_after_submit = True
				unreconcile_doc.flags.ignore_links = True
				unreconcile_doc.save(ignore_permissions=True)

		# delete docs upon parent doc deletion
		unreconcile_docs = frappe.db.get_all("Unreconcile Payment", filters={"voucher_no": self.name})
		for x in unreconcile_docs:
			_doc = frappe.get_doc("Unreconcile Payment", x.name)
			if _doc.docstatus == 1:
				_doc.cancel()
			_doc.delete()

	def _remove_references_in_repost_doctypes(self):
		repost_doctypes = ["Repost Payment Ledger Items", "Repost Accounting Ledger Items"]

		for _doctype in repost_doctypes:
			dt = frappe.qb.DocType(_doctype)
			rows = (
				frappe.qb.from_(dt)
				.select(dt.name, dt.parent, dt.parenttype)
				.where((dt.voucher_type == self.doctype) & (dt.voucher_no == self.name))
				.run(as_dict=True)
			)

			if rows:
				references_map = frappe._dict()
				for x in rows:
					references_map.setdefault((x.parenttype, x.parent), []).append(x.name)

				for doc, rows in references_map.items():
					repost_doc = frappe.get_doc(doc[0], doc[1])

					for row in rows:
						if _doctype == "Repost Payment Ledger Items":
							repost_doc.remove(repost_doc.get("repost_vouchers", {"name": row})[0])
						else:
							repost_doc.remove(repost_doc.get("vouchers", {"name": row})[0])

					repost_doc.flags.ignore_validate_update_after_submit = True
					repost_doc.flags.ignore_links = True
					repost_doc.save(ignore_permissions=True)

	def on_trash(self):
		from erpnext.accounts.utils import delete_exchange_gain_loss_journal

		self._remove_references_in_repost_doctypes()
		self._remove_references_in_unreconcile()
		self.remove_serial_and_batch_bundle()

		# delete sl and gl entries on deletion of transaction
		if frappe.db.get_single_value("Accounts Settings", "delete_linked_ledger_entries"):
			# delete linked exchange gain/loss journal
			delete_exchange_gain_loss_journal(self)

			ple = frappe.qb.DocType("Payment Ledger Entry")
			frappe.qb.from_(ple).delete().where(
				(ple.voucher_type == self.doctype) & (ple.voucher_no == self.name)
				| (
					(ple.against_voucher_type == self.doctype)
					& (ple.against_voucher_no == self.name)
					& ple.delinked
					== 1
				)
			).run()
			frappe.db.sql(
				"delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s", (self.doctype, self.name)
			)
			frappe.db.sql(
				"delete from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s",
				(self.doctype, self.name),
			)

	def remove_serial_and_batch_bundle(self):
		bundles = frappe.get_all(
			"Serial and Batch Bundle",
			filters={"voucher_type": self.doctype, "voucher_no": self.name, "docstatus": ("!=", 1)},
		)

		for bundle in bundles:
			frappe.delete_doc("Serial and Batch Bundle", bundle.name)

		batches = frappe.get_all(
			"Batch", filters={"reference_doctype": self.doctype, "reference_name": self.name}
		)
		for row in batches:
			frappe.delete_doc("Batch", row.name)

	def validate_return_against_account(self):
		if self.doctype in ["Sales Invoice", "Purchase Invoice"] and self.is_return and self.return_against:
			cr_dr_account_field = "debit_to" if self.doctype == "Sales Invoice" else "credit_to"
			original_account = frappe.get_value(self.doctype, self.return_against, cr_dr_account_field)
			if original_account != self.get(cr_dr_account_field):
				frappe.throw(
					_(
						"Please set {0} to {1}, the same account that was used in the original invoice {2}."
					).format(
						frappe.bold(_(self.meta.get_label(cr_dr_account_field), context=self.doctype)),
						frappe.bold(original_account),
						frappe.bold(self.return_against),
					)
				)

	def validate_deferred_income_expense_account(self):
		field_map = {
			"Sales Invoice": "deferred_revenue_account",
			"Purchase Invoice": "deferred_expense_account",
		}

		for item in self.get("items"):
			if item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"):
				if not item.get(field_map.get(self.doctype)):
					default_deferred_account = frappe.get_cached_value(
						"Company", self.company, "default_" + field_map.get(self.doctype)
					)
					if not default_deferred_account:
						frappe.throw(
							_(
								"Row #{0}: Please update deferred revenue/expense account in item row or default account in company master"
							).format(item.idx)
						)
					else:
						item.set(field_map.get(self.doctype), default_deferred_account)

	def validate_auto_repeat_subscription_dates(self):
		if self.get("from_date") and self.get("to_date") and getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("To Date cannot be before From Date"), title=_("Invalid Auto Repeat Date"))

	def validate_deferred_start_and_end_date(self):
		for d in self.items:
			if d.get("enable_deferred_revenue") or d.get("enable_deferred_expense"):
				if not (d.service_start_date and d.service_end_date):
					frappe.throw(
						_("Row #{0}: Service Start and End Date is required for deferred accounting").format(
							d.idx
						)
					)
				elif getdate(d.service_start_date) > getdate(d.service_end_date):
					frappe.throw(
						_("Row #{0}: Service Start Date cannot be greater than Service End Date").format(
							d.idx
						)
					)
				elif getdate(self.posting_date) > getdate(d.service_end_date):
					frappe.throw(
						_("Row #{0}: Service End Date cannot be before Invoice Posting Date").format(d.idx)
					)

	def validate_invoice_documents_schedule(self):
		self.validate_payment_schedule_dates()
		self.set_due_date()
		self.set_payment_schedule()
		if not self.get("ignore_default_payment_terms_template"):
			self.validate_payment_schedule_amount()
			self.validate_due_date()
		self.validate_advance_entries()

	def validate_non_invoice_documents_schedule(self):
		self.set_payment_schedule()
		self.validate_payment_schedule_dates()
		self.validate_payment_schedule_amount()

	def validate_all_documents_schedule(self):
		if self.doctype in ("Sales Invoice", "Purchase Invoice") and not self.is_return:
			self.validate_invoice_documents_schedule()
		elif self.doctype in ("Quotation", "Purchase Order", "Sales Order"):
			self.validate_non_invoice_documents_schedule()

	def before_print(self, settings=None):
		if self.doctype in [
			"Purchase Order",
			"Sales Order",
			"Sales Invoice",
			"Purchase Invoice",
			"Supplier Quotation",
			"Purchase Receipt",
			"Delivery Note",
			"Quotation",
		]:
			if self.get("group_same_items"):
				self.group_similar_items()

			df = self.meta.get_field("discount_amount")
			if self.get("discount_amount") and hasattr(self, "taxes") and not len(self.taxes):
				df.set("print_hide", 0)
				self.discount_amount = -self.discount_amount
			else:
				df.set("print_hide", 1)

		set_print_templates_for_item_table(self, settings)
		set_print_templates_for_taxes(self, settings)

	def calculate_paid_amount(self):
		if hasattr(self, "is_pos") or hasattr(self, "is_paid"):
			is_paid = self.get("is_pos") or self.get("is_paid")

			if is_paid:
				if not self.cash_bank_account:
					# show message that the amount is not paid
					frappe.throw(
						_(
							"Note: Payment Entry will not be created since 'Cash or Bank Account' was not specified"
						)
					)

				if cint(self.is_return) and self.grand_total > self.paid_amount:
					self.paid_amount = flt(flt(self.grand_total), self.precision("paid_amount"))

				elif not flt(self.paid_amount) and flt(self.outstanding_amount) > 0:
					self.paid_amount = flt(flt(self.outstanding_amount), self.precision("paid_amount"))

				self.base_paid_amount = flt(
					self.paid_amount * self.conversion_rate, self.precision("base_paid_amount")
				)

	def set_missing_values(self, for_validate=False):
		if frappe.flags.in_test:
			for fieldname in ["posting_date", "transaction_date"]:
				if self.meta.get_field(fieldname) and not self.get(fieldname):
					self.set(fieldname, today())
					break

	def calculate_taxes_and_totals(self):
		from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

		calculate_taxes_and_totals(self)

		if self.doctype in (
			"Sales Order",
			"Delivery Note",
			"Sales Invoice",
			"POS Invoice",
		):
			self.calculate_commission()
			self.calculate_contribution()

	def validate_date_with_fiscal_year(self):
		if self.meta.get_field("fiscal_year"):
			date_field = None
			if self.meta.get_field("posting_date"):
				date_field = "posting_date"
			elif self.meta.get_field("transaction_date"):
				date_field = "transaction_date"

			if date_field and self.get(date_field):
				validate_fiscal_year(
					self.get(date_field),
					self.fiscal_year,
					self.company,
					self.meta.get_label(date_field),
					self,
				)

	def validate_party_accounts(self):
		if self.doctype not in ("Sales Invoice", "Purchase Invoice"):
			return

		if self.doctype == "Sales Invoice":
			party_account_field = "debit_to"
			item_field = "income_account"
		else:
			party_account_field = "credit_to"
			item_field = "expense_account"

		for item in self.get("items"):
			if item.get(item_field) == self.get(party_account_field):
				frappe.throw(
					_("Row {0}: {1} {2} cannot be same as {3} (Party Account) {4}").format(
						item.idx,
						frappe.bold(frappe.unscrub(item_field)),
						item.get(item_field),
						frappe.bold(frappe.unscrub(party_account_field)),
						self.get(party_account_field),
					)
				)

	def validate_inter_company_reference(self):
		if self.get("is_return"):
			return

		if self.doctype not in ("Purchase Invoice", "Purchase Receipt"):
			return

		if self.is_internal_transfer():
			if not (
				self.get("inter_company_reference")
				or self.get("inter_company_invoice_reference")
				or self.get("inter_company_order_reference")
			) and not self.get("is_return"):
				msg = _("Internal Sale or Delivery Reference missing.")
				msg += _("Please create purchase from internal sale or delivery document itself")
				frappe.throw(msg, title=_("Internal Sales Reference Missing"))

			label = "Delivery Note Item" if self.doctype == "Purchase Receipt" else "Sales Invoice Item"

			field = frappe.scrub(label)

			for row in self.get("items"):
				if not row.get(field):
					msg = f"At Row {row.idx}: The field {bold(label)} is mandatory for internal transfer"
					frappe.throw(_(msg), title=_("Internal Transfer Reference Missing"))

	def disable_pricing_rule_on_internal_transfer(self):
		if not self.get("ignore_pricing_rule") and self.is_internal_transfer():
			self.ignore_pricing_rule = 1
			frappe.msgprint(
				_("Disabled pricing rules since this {} is an internal transfer").format(self.doctype),
				alert=1,
			)

	def disable_tax_included_prices_for_internal_transfer(self):
		if self.is_internal_transfer():
			tax_updated = False
			for tax in self.get("taxes"):
				if tax.get("included_in_print_rate"):
					tax.included_in_print_rate = 0
					tax_updated = True

			if tax_updated:
				frappe.msgprint(
					_("Disabled tax included prices since this {} is an internal transfer").format(
						self.doctype
					),
					alert=1,
				)

	def validate_due_date(self):
		if self.get("is_pos") or self.doctype not in ["Sales Invoice", "Purchase Invoice"]:
			return

		from erpnext.accounts.party import validate_due_date

		posting_date = (
			self.posting_date if self.doctype == "Sales Invoice" else (self.bill_date or self.posting_date)
		)

		# skip due date validation for records via Data Import
		if frappe.flags.in_import and getdate(self.due_date) < getdate(posting_date):
			self.due_date = posting_date

		elif self.doctype == "Sales Invoice":
			if not self.due_date:
				frappe.throw(_("Due Date is mandatory"))

			validate_due_date(
				posting_date,
				self.due_date,
				self.payment_terms_template,
			)
		elif self.doctype == "Purchase Invoice":
			validate_due_date(
				posting_date,
				self.due_date,
				self.bill_date,
				self.payment_terms_template,
			)

	def set_price_list_currency(self, buying_or_selling):
		if self.meta.get_field("posting_date"):
			transaction_date = self.posting_date
		else:
			transaction_date = self.transaction_date

		if self.meta.get_field("currency"):
			# price list part
			if buying_or_selling.lower() == "selling":
				fieldname = "selling_price_list"
				args = "for_selling"
			else:
				fieldname = "buying_price_list"
				args = "for_buying"

			if self.meta.get_field(fieldname) and self.get(fieldname):
				self.price_list_currency = frappe.db.get_value("Price List", self.get(fieldname), "currency")

				if self.price_list_currency == self.company_currency:
					self.plc_conversion_rate = 1.0

				elif not self.plc_conversion_rate:
					self.plc_conversion_rate = get_exchange_rate(
						self.price_list_currency, self.company_currency, transaction_date, args
					)

			# currency
			if not self.currency:
				self.currency = self.price_list_currency
				self.conversion_rate = self.plc_conversion_rate
			elif self.currency == self.company_currency:
				self.conversion_rate = 1.0
			elif not self.conversion_rate:
				self.conversion_rate = get_exchange_rate(
					self.currency, self.company_currency, transaction_date, args
				)

			if (
				self.currency
				and buying_or_selling == "Buying"
				and frappe.db.get_single_value("Buying Settings", "use_transaction_date_exchange_rate")
				and self.doctype == "Purchase Invoice"
			):
				self.use_transaction_date_exchange_rate = True
				self.conversion_rate = get_exchange_rate(
					self.currency, self.company_currency, transaction_date, args
				)

	def set_missing_item_details(self, for_validate=False):
		"""set missing item values"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
				document_type = f"{self.doctype} Item"
				parent_dict.update({"document_type": document_type})

			# party_name field used for customer in quotation
			if (
				self.doctype == "Quotation"
				and self.quotation_to == "Customer"
				and parent_dict.get("party_name")
			):
				parent_dict.update({"customer": parent_dict.get("party_name")})

			self.pricing_rules = []

			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())

					args["doctype"] = self.doctype
					args["name"] = self.name
					args["child_doctype"] = item.doctype
					args["child_docname"] = item.name
					args["ignore_pricing_rule"] = (
						self.ignore_pricing_rule if hasattr(self, "ignore_pricing_rule") else 0
					)

					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					ret = get_item_details(args, self, for_validate=for_validate, overwrite_warehouse=False)
					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if item.get(fieldname) is None or fieldname in force_item_fields:
								item.set(fieldname, value)

							elif fieldname in ["cost_center", "conversion_factor"] and not item.get(
								fieldname
							):
								item.set(fieldname, value)
							elif fieldname == "item_tax_rate" and not (
								self.get("is_return") and self.get("return_against")
							):
								item.set(fieldname, value)
							elif fieldname == "serial_no":
								# Ensure that serial numbers are matched against Stock UOM
								item_conversion_factor = item.get("conversion_factor") or 1.0
								item_qty = abs(item.get("qty")) * item_conversion_factor

								if item_qty != len(get_serial_nos(item.get("serial_no"))):
									item.set(fieldname, value)

							elif (
								ret.get("pricing_rule_removed")
								and value is not None
								and fieldname
								in [
									"discount_percentage",
									"discount_amount",
									"rate",
									"margin_rate_or_amount",
									"margin_type",
									"remove_free_item",
								]
							):
								# reset pricing rule fields if pricing_rule_removed
								item.set(fieldname, value)

					if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field(
						"is_fixed_asset"
					):
						item.set("is_fixed_asset", ret.get("is_fixed_asset", 0))

					# Double check for cost center
					# Items add via promotional scheme may not have cost center set
					if hasattr(item, "cost_center") and not item.get("cost_center"):
						item.set(
							"cost_center",
							self.get("cost_center") or erpnext.get_default_cost_center(self.company),
						)

					if ret.get("pricing_rules"):
						self.apply_pricing_rule_on_items(item, ret)
						self.set_pricing_rule_details(item, ret)
				else:
					# Transactions line item without item code

					uom = item.get("uom")
					stock_uom = item.get("stock_uom")
					if bool(uom) != bool(stock_uom):  # xor
						item.stock_uom = item.uom = uom or stock_uom

					# UOM cannot be zero so substitute as 1
					item.conversion_factor = (
						get_uom_conv_factor(item.get("uom"), item.get("stock_uom"))
						or item.get("conversion_factor")
						or 1
					)

			if self.doctype == "Purchase Invoice":
				self.set_expense_account(for_validate)

	def apply_pricing_rule_on_items(self, item, pricing_rule_args):
		if not pricing_rule_args.get("validate_applied_rule", 0):
			# if user changed the discount percentage then set user's discount percentage ?
			if pricing_rule_args.get("price_or_product_discount") == "Price":
				item.set("pricing_rules", pricing_rule_args.get("pricing_rules"))
				if pricing_rule_args.get("apply_rule_on_other_items"):
					other_items = json.loads(pricing_rule_args.get("apply_rule_on_other_items"))
					if other_items and item.item_code not in other_items:
						return

				item.set("discount_percentage", pricing_rule_args.get("discount_percentage"))
				item.set("discount_amount", pricing_rule_args.get("discount_amount"))
				if pricing_rule_args.get("pricing_rule_for") == "Rate":
					item.set("price_list_rate", pricing_rule_args.get("price_list_rate"))

				if item.get("price_list_rate"):
					item.rate = flt(
						item.price_list_rate * (1.0 - (flt(item.discount_percentage) / 100.0)),
						item.precision("rate"),
					)

					if item.get("discount_amount"):
						item.rate = item.price_list_rate - item.discount_amount

				if item.get("apply_discount_on_discounted_rate") and pricing_rule_args.get("rate"):
					item.rate = pricing_rule_args.get("rate")

			elif pricing_rule_args.get("free_item_data"):
				apply_pricing_rule_for_free_items(self, pricing_rule_args.get("free_item_data"))

		elif pricing_rule_args.get("validate_applied_rule"):
			for pricing_rule in get_applied_pricing_rules(item.get("pricing_rules")):
				pricing_rule_doc = frappe.get_cached_doc("Pricing Rule", pricing_rule)
				for field in ["discount_percentage", "discount_amount", "rate"]:
					if item.get(field) < pricing_rule_doc.get(field):
						title = get_link_to_form("Pricing Rule", pricing_rule)

						frappe.msgprint(
							_("Row {0}: user has not applied the rule {1} on the item {2}").format(
								item.idx, frappe.bold(title), frappe.bold(item.item_code)
							)
						)

	def set_pricing_rule_details(self, item_row, args):
		pricing_rules = get_applied_pricing_rules(args.get("pricing_rules"))
		if not pricing_rules:
			return

		for pricing_rule in pricing_rules:
			self.append(
				"pricing_rules",
				{
					"pricing_rule": pricing_rule,
					"item_code": item_row.item_code,
					"child_docname": item_row.name,
					"rule_applied": True,
				},
			)

	def set_taxes(self):
		if not self.meta.get_field("taxes"):
			return

		tax_master_doctype = self.meta.get_field("taxes_and_charges").options

		if (self.is_new() or self.is_pos_profile_changed()) and not self.get("taxes"):
			if self.company and not self.get("taxes_and_charges"):
				# get the default tax master
				self.taxes_and_charges = frappe.db.get_value(
					tax_master_doctype, {"is_default": 1, "company": self.company}
				)

			self.append_taxes_from_master(tax_master_doctype)

	def is_pos_profile_changed(self):
		if (
			self.doctype == "Sales Invoice"
			and self.is_pos
			and self.pos_profile != frappe.db.get_value("Sales Invoice", self.name, "pos_profile")
		):
			return True

	def append_taxes_from_master(self, tax_master_doctype=None):
		if self.get("taxes_and_charges"):
			if not tax_master_doctype:
				tax_master_doctype = self.meta.get_field("taxes_and_charges").options

			self.extend("taxes", get_taxes_and_charges(tax_master_doctype, self.get("taxes_and_charges")))

	def append_taxes_from_item_tax_template(self):
		if not frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template"):
			return

		for row in self.items:
			item_tax_rate = row.get("item_tax_rate")
			if not item_tax_rate:
				continue

			if isinstance(item_tax_rate, str):
				item_tax_rate = parse_json(item_tax_rate)

			for account_head, _rate in item_tax_rate.items():
				row = self.get_tax_row(account_head)

				if not row:
					self.append(
						"taxes",
						{
							"charge_type": "On Net Total",
							"account_head": account_head,
							"rate": 0,
							"description": account_head,
						},
					)

	def get_tax_row(self, account_head):
		for row in self.taxes:
			if row.account_head == account_head:
				return row

	def set_other_charges(self):
		self.set("taxes", [])
		self.set_taxes()

	def validate_enabled_taxes_and_charges(self):
		taxes_and_charges_doctype = self.meta.get_options("taxes_and_charges")
		if self.taxes_and_charges and frappe.get_cached_value(
			taxes_and_charges_doctype, self.taxes_and_charges, "disabled"
		):
			frappe.throw(_("{0} '{1}' is disabled").format(taxes_and_charges_doctype, self.taxes_and_charges))

	def validate_tax_account_company(self):
		for d in self.get("taxes"):
			if d.account_head:
				tax_account_company = frappe.get_cached_value("Account", d.account_head, "company")
				if tax_account_company != self.company:
					frappe.throw(
						_("Row #{0}: Account {1} does not belong to company {2}").format(
							d.idx, d.account_head, self.company
						)
					)

	def get_gl_dict(self, args, account_currency=None, item=None):
		"""this method populates the common properties of a gl entry record"""

		posting_date = args.get("posting_date") or self.get("posting_date")
		fiscal_years = get_fiscal_years(posting_date, company=self.company)
		if len(fiscal_years) > 1:
			frappe.throw(
				_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
					formatdate(posting_date)
				)
			)
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict(
			{
				"company": self.company,
				"posting_date": posting_date,
				"fiscal_year": fiscal_year,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"remarks": self.get("remarks") or self.get("remark"),
				"debit": 0,
				"credit": 0,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": 0,
				"is_opening": self.get("is_opening") or "No",
				"party_type": None,
				"party": None,
				"project": self.get("project"),
				"post_net_value": args.get("post_net_value"),
				"voucher_detail_no": args.get("voucher_detail_no"),
				"voucher_subtype": self.get_voucher_subtype(),
			}
		)

		with temporary_flag("company", self.company):
			update_gl_dict_with_regional_fields(self, gl_dict)

		accounting_dimensions = get_accounting_dimensions()
		dimension_dict = frappe._dict()

		for dimension in accounting_dimensions:
			dimension_dict[dimension] = self.get(dimension)
			if item and item.get(dimension):
				dimension_dict[dimension] = item.get(dimension)

		gl_dict.update(dimension_dict)
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		if gl_dict.account and self.doctype not in [
			"Journal Entry",
			"Period Closing Voucher",
			"Payment Entry",
			"Purchase Receipt",
			"Purchase Invoice",
			"Stock Entry",
		]:
			self.validate_account_currency(gl_dict.account, account_currency)

		if gl_dict.account and self.doctype not in [
			"Journal Entry",
			"Period Closing Voucher",
			"Payment Entry",
		]:
			set_balance_in_account_currency(
				gl_dict, account_currency, self.get("conversion_rate"), self.company_currency
			)

		# Update details in transaction currency
		gl_dict.update(
			{
				"transaction_currency": self.get("currency") or self.company_currency,
				"transaction_exchange_rate": item.get("exchange_rate", 1)
				if self.doctype == "Journal Entry" and item
				else self.get("conversion_rate", 1),
				"debit_in_transaction_currency": self.get_value_in_transaction_currency(
					account_currency, gl_dict, "debit"
				),
				"credit_in_transaction_currency": self.get_value_in_transaction_currency(
					account_currency, gl_dict, "credit"
				),
			}
		)

		if not args.get("against_voucher_type") and self.get("against_voucher_type"):
			gl_dict.update({"against_voucher_type": self.get("against_voucher_type")})

		if not args.get("against_voucher") and self.get("against_voucher"):
			gl_dict.update({"against_voucher": self.get("against_voucher")})

		return gl_dict

	def get_voucher_subtype(self):
		voucher_subtypes = {
			"Journal Entry": "voucher_type",
			"Payment Entry": "payment_type",
			"Stock Entry": "stock_entry_type",
			"Asset Capitalization": "entry_type",
		}

		for method_name in frappe.get_hooks("voucher_subtypes"):
			voucher_subtype = frappe.get_attr(method_name)(self)

			if voucher_subtype:
				return voucher_subtype

		if self.doctype in voucher_subtypes:
			return self.get(voucher_subtypes[self.doctype])
		elif self.doctype == "Purchase Receipt" and self.is_return:
			return "Purchase Return"
		elif self.doctype == "Delivery Note" and self.is_return:
			return "Sales Return"
		elif (self.doctype == "Sales Invoice" and self.is_return) or self.doctype == "Purchase Invoice":
			return "Credit Note"
		elif (self.doctype == "Purchase Invoice" and self.is_return) or self.doctype == "Sales Invoice":
			return "Debit Note"

		return self.doctype

	def get_value_in_transaction_currency(self, account_currency, gl_dict, field):
		if account_currency == self.get("currency"):
			return gl_dict.get(field + "_in_account_currency")
		else:
			return flt(gl_dict.get(field, 0) / self.get("conversion_rate", 1))

	def validate_zero_qty_for_return_invoices_with_stock(self):
		rows = []
		for item in self.items:
			if not flt(item.qty):
				rows.append(item)
		if rows:
			frappe.throw(
				_(
					"For Return Invoices with Stock effect, '0' qty Items are not allowed. Following rows are affected: {0}"
				).format(frappe.bold(comma_and(["#" + str(x.idx) for x in rows])))
			)

	def validate_qty_is_not_zero(self):
		if self.doctype == "Purchase Receipt":
			return

		for item in self.items:
			if not flt(item.qty):
				frappe.throw(
					msg=_("Row #{0}: Item quantity cannot be zero").format(item.idx),
					title=_("Invalid Quantity"),
					exc=InvalidQtyError,
				)

	def validate_account_currency(self, account, account_currency=None):
		valid_currency = [self.company_currency]
		if self.get("currency") and self.currency != self.company_currency:
			valid_currency.append(self.currency)

		if account_currency not in valid_currency:
			frappe.throw(
				_("Account {0} is invalid. Account Currency must be {1}").format(
					account, (" " + _("or") + " ").join(valid_currency)
				)
			)

	def clear_unallocated_advances(self, childtype, parentfield):
		self.set(parentfield, self.get(parentfield, {"allocated_amount": ["not in", [0, None, ""]]}))

		frappe.db.sql(
			"""delete from `tab{}` where parentfield={} and parent = {}
			and allocated_amount = 0""".format(childtype, "%s", "%s"),
			(parentfield, self.name),
		)

	@frappe.whitelist()
	def apply_shipping_rule(self):
		if self.shipping_rule:
			shipping_rule = frappe.get_doc("Shipping Rule", self.shipping_rule)
			shipping_rule.apply(self)
			self.calculate_taxes_and_totals()

	def get_shipping_address(self):
		"""Returns Address object from shipping address fields if present"""

		# shipping address fields can be `shipping_address_name` or `shipping_address`
		# try getting value from both

		for fieldname in ("shipping_address_name", "shipping_address"):
			shipping_field = self.meta.get_field(fieldname)
			if shipping_field and shipping_field.fieldtype == "Link":
				if self.get(fieldname):
					return frappe.get_doc("Address", self.get(fieldname))

		return {}

	@frappe.whitelist()
	def set_advances(self):
		"""Returns list of advances against Account, Party, Reference"""

		res = self.get_advance_entries(
			include_unallocated=not cint(self.get("only_include_allocated_payments"))
		)

		self.set("advances", [])
		advance_allocated = 0
		for d in res:
			if self.get("party_account_currency") == self.company_currency:
				amount = self.get("base_rounded_total") or self.base_grand_total
			else:
				amount = self.get("rounded_total") or self.grand_total
			allocated_amount = min(amount - advance_allocated, d.amount)
			advance_allocated += flt(allocated_amount)

			advance_row = {
				"doctype": self.doctype + " Advance",
				"reference_type": d.reference_type,
				"reference_name": d.reference_name,
				"reference_row": d.reference_row,
				"remarks": d.remarks,
				"advance_amount": flt(d.amount),
				"allocated_amount": allocated_amount,
				"ref_exchange_rate": flt(d.exchange_rate),  # exchange_rate of advance entry
			}
			if d.get("paid_from"):
				advance_row["account"] = d.paid_from
			if d.get("paid_to"):
				advance_row["account"] = d.paid_to

			self.append("advances", advance_row)

	def get_advance_entries(self, include_unallocated=True):
		party_account = []
		if self.doctype == "Sales Invoice":
			party_type = "Customer"
			party = self.customer
			amount_field = "credit_in_account_currency"
			order_field = "sales_order"
			order_doctype = "Sales Order"
			party_account.append(self.debit_to)
		else:
			party_type = "Supplier"
			party = self.supplier
			amount_field = "debit_in_account_currency"
			order_field = "purchase_order"
			order_doctype = "Purchase Order"
			party_account.append(self.credit_to)

		party_account.extend(
			get_party_account(party_type, party=party, company=self.company, include_advance=True)
		)

		order_list = list(set(d.get(order_field) for d in self.get("items") if d.get(order_field)))

		journal_entries = get_advance_journal_entries(
			party_type, party, party_account, amount_field, order_doctype, order_list, include_unallocated
		)

		payment_entries = get_advance_payment_entries_for_regional(
			party_type, party, party_account, order_doctype, order_list, include_unallocated
		)

		res = journal_entries + payment_entries

		return res

	def is_inclusive_tax(self):
		is_inclusive = cint(frappe.db.get_single_value("Accounts Settings", "show_inclusive_tax_in_print"))

		if is_inclusive:
			is_inclusive = 0
			if self.get("taxes", filters={"included_in_print_rate": 1}):
				is_inclusive = 1

		return is_inclusive

	def should_show_taxes_as_table_in_print(self):
		return cint(frappe.db.get_single_value("Accounts Settings", "show_taxes_as_table_in_print"))

	def validate_advance_entries(self):
		order_field = "sales_order" if self.doctype == "Sales Invoice" else "purchase_order"
		order_list = list(set(d.get(order_field) for d in self.get("items") if d.get(order_field)))

		if not order_list:
			return

		advance_entries = self.get_advance_entries(include_unallocated=False)

		if advance_entries:
			advance_entries_against_si = [d.reference_name for d in self.get("advances")]
			for d in advance_entries:
				if not advance_entries_against_si or d.reference_name not in advance_entries_against_si:
					frappe.msgprint(
						_(
							"Payment Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice."
						).format(d.reference_name, d.against_order)
					)

	def set_advance_gain_or_loss(self):
		if self.get("conversion_rate") == 1 or not self.get("advances"):
			return

		is_purchase_invoice = self.doctype == "Purchase Invoice"
		party_account = self.credit_to if is_purchase_invoice else self.debit_to
		if get_account_currency(party_account) != self.currency:
			return

		for d in self.get("advances"):
			advance_exchange_rate = d.ref_exchange_rate
			if d.allocated_amount and self.conversion_rate != advance_exchange_rate:
				base_allocated_amount_in_ref_rate = advance_exchange_rate * d.allocated_amount
				base_allocated_amount_in_inv_rate = self.conversion_rate * d.allocated_amount
				difference = base_allocated_amount_in_ref_rate - base_allocated_amount_in_inv_rate

				d.exchange_gain_loss = difference

	def make_precision_loss_gl_entry(self, gl_entries):
		round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(
			self.company, "Purchase Invoice", self.name, self.use_company_roundoff_cost_center
		)

		precision_loss = self.get("base_net_total") - flt(
			self.get("net_total") * self.conversion_rate, self.precision("net_total")
		)

		credit_or_debit = "credit" if self.doctype == "Purchase Invoice" else "debit"
		against = self.supplier if self.doctype == "Purchase Invoice" else self.customer

		if precision_loss:
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": round_off_account,
						"against": against,
						credit_or_debit: precision_loss,
						"cost_center": round_off_cost_center
						if self.use_company_roundoff_cost_center
						else self.cost_center or round_off_cost_center,
						"remarks": _("Net total calculation precision loss"),
					}
				)
			)

	def gain_loss_journal_already_booked(
		self,
		gain_loss_account,
		exc_gain_loss,
		ref2_dt,
		ref2_dn,
		ref2_detail_no,
	) -> bool:
		"""
		Check if gain/loss is booked
		"""
		if res := frappe.db.get_all(
			"Journal Entry Account",
			filters={
				"docstatus": 1,
				"account": gain_loss_account,
				"reference_type": ref2_dt,  # this will be Journal Entry
				"reference_name": ref2_dn,
				"reference_detail_no": ref2_detail_no,
			},
			pluck="parent",
		):
			# deduplicate
			res = list({x for x in res})
			if exc_vouchers := frappe.db.get_all(
				"Journal Entry",
				filters={"name": ["in", res], "voucher_type": "Exchange Gain Or Loss"},
				fields=["voucher_type", "total_debit", "total_credit"],
			):
				booked_voucher = exc_vouchers[0]
				if (
					booked_voucher.total_debit == exc_gain_loss
					and booked_voucher.total_credit == exc_gain_loss
					and booked_voucher.voucher_type == "Exchange Gain Or Loss"
				):
					return True
		return False

	def make_exchange_gain_loss_journal(
		self, args: dict | None = None, dimensions_dict: dict | None = None
	) -> None:
		"""
		Make Exchange Gain/Loss journal for Invoices and Payments
		"""
		# Cancelling existing exchange gain/loss journals is handled during the `on_cancel` event.
		# see accounts/utils.py:cancel_exchange_gain_loss_journal()
		if self.docstatus == 1:
			if dimensions_dict is None:
				dimensions_dict = frappe._dict()
				active_dimensions = get_dimensions()[0]
				for dim in active_dimensions:
					dimensions_dict[dim.fieldname] = self.get(dim.fieldname)

			if self.get("doctype") == "Journal Entry":
				# 'args' is populated with exchange gain/loss account and the amount to be booked.
				# These are generated by Sales/Purchase Invoice during reconciliation and advance allocation.
				# and below logic is only for such scenarios
				if args:
					precision = get_currency_precision()
					for arg in args:
						# Advance section uses `exchange_gain_loss` and reconciliation uses `difference_amount`
						if (
							flt(arg.get("difference_amount", 0), precision) != 0
							or flt(arg.get("exchange_gain_loss", 0), precision) != 0
						) and arg.get("difference_account"):
							party_account = arg.get("account")
							gain_loss_account = arg.get("difference_account")
							difference_amount = arg.get("difference_amount") or arg.get("exchange_gain_loss")
							if difference_amount > 0:
								dr_or_cr = "debit" if arg.get("party_type") == "Customer" else "credit"
							else:
								dr_or_cr = "credit" if arg.get("party_type") == "Customer" else "debit"

							reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

							if not self.gain_loss_journal_already_booked(
								gain_loss_account,
								difference_amount,
								self.doctype,
								self.name,
								arg.get("referenced_row"),
							):
								posting_date = arg.get("difference_posting_date") or frappe.db.get_value(
									arg.voucher_type, arg.voucher_no, "posting_date"
								)
								je = create_gain_loss_journal(
									self.company,
									posting_date,
									arg.get("party_type"),
									arg.get("party"),
									party_account,
									gain_loss_account,
									difference_amount,
									dr_or_cr,
									reverse_dr_or_cr,
									arg.get("against_voucher_type"),
									arg.get("against_voucher"),
									arg.get("idx"),
									self.doctype,
									self.name,
									arg.get("referenced_row"),
									arg.get("cost_center"),
									dimensions_dict,
								)
								frappe.msgprint(
									_("Exchange Gain/Loss amount has been booked through {0}").format(
										get_link_to_form("Journal Entry", je)
									)
								)

			if self.get("doctype") == "Payment Entry":
				# For Payment Entry, exchange_gain_loss field in the `references` table is the trigger for journal creation
				gain_loss_to_book = [x for x in self.references if x.exchange_gain_loss != 0]
				booked = []
				if gain_loss_to_book:
					[x.reference_doctype for x in gain_loss_to_book]
					[x.reference_name for x in gain_loss_to_book]
					je = qb.DocType("Journal Entry")
					jea = qb.DocType("Journal Entry Account")
					parents = (
						qb.from_(jea)
						.select(jea.parent)
						.where(
							(jea.reference_type == "Payment Entry")
							& (jea.reference_name == self.name)
							& (jea.docstatus == 1)
						)
						.run()
					)

					booked = []
					if parents:
						booked = (
							qb.from_(je)
							.inner_join(jea)
							.on(je.name == jea.parent)
							.select(jea.reference_type, jea.reference_name, jea.reference_detail_no)
							.where(
								(je.docstatus == 1)
								& (je.name.isin(parents))
								& (je.voucher_type == "Exchange Gain or Loss")
							)
							.run()
						)

				for d in gain_loss_to_book:
					# Filter out References for which Gain/Loss is already booked
					if d.exchange_gain_loss and (
						(d.reference_doctype, d.reference_name, str(d.idx)) not in booked
					):
						if self.book_advance_payments_in_separate_party_account:
							party_account = d.account
						else:
							if self.payment_type == "Receive":
								party_account = self.paid_from
							elif self.payment_type == "Pay":
								party_account = self.paid_to

						dr_or_cr = "debit" if d.exchange_gain_loss > 0 else "credit"

						# Inverse debit/credit for payable accounts
						if self.is_payable_account(d.reference_doctype, party_account):
							dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

						reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

						gain_loss_account = frappe.get_cached_value(
							"Company", self.company, "exchange_gain_loss_account"
						)

						je = create_gain_loss_journal(
							self.company,
							args.get("difference_posting_date") if args else self.posting_date,
							self.party_type,
							self.party,
							party_account,
							gain_loss_account,
							d.exchange_gain_loss,
							dr_or_cr,
							reverse_dr_or_cr,
							d.reference_doctype,
							d.reference_name,
							d.idx,
							self.doctype,
							self.name,
							d.idx,
							self.cost_center,
							dimensions_dict,
						)
						frappe.msgprint(
							_("Exchange Gain/Loss amount has been booked through {0}").format(
								get_link_to_form("Journal Entry", je)
							)
						)

	def is_payable_account(self, reference_doctype, account):
		if reference_doctype == "Purchase Invoice" or (
			reference_doctype == "Journal Entry"
			and frappe.get_cached_value("Account", account, "account_type") == "Payable"
		):
			return True
		return False

	def update_against_document_in_jv(self):
		"""
		Links invoice and advance voucher:
		        1. cancel advance voucher
		        2. split into multiple rows if partially adjusted, assign against voucher
		        3. submit advance voucher
		"""

		if self.doctype == "Sales Invoice":
			party_type = "Customer"
			party = self.customer
			party_account = self.debit_to
			dr_or_cr = "credit_in_account_currency"
		else:
			party_type = "Supplier"
			party = self.supplier
			party_account = self.credit_to
			dr_or_cr = "debit_in_account_currency"

		lst = []
		for d in self.get("advances"):
			if flt(d.allocated_amount) > 0:
				args = frappe._dict(
					{
						"voucher_type": d.reference_type,
						"voucher_no": d.reference_name,
						"voucher_detail_no": d.reference_row,
						"against_voucher_type": self.doctype,
						"against_voucher": self.name,
						"account": party_account,
						"party_type": party_type,
						"party": party,
						"is_advance": "Yes",
						"dr_or_cr": dr_or_cr,
						"unadjusted_amount": flt(d.advance_amount),
						"allocated_amount": flt(d.allocated_amount),
						"precision": d.precision("advance_amount"),
						"exchange_rate": (
							self.conversion_rate
							if self.party_account_currency != self.company_currency
							else 1
						),
						"grand_total": (
							self.base_grand_total
							if self.party_account_currency == self.company_currency
							else self.grand_total
						),
						"outstanding_amount": self.outstanding_amount,
						"difference_account": frappe.get_cached_value(
							"Company", self.company, "exchange_gain_loss_account"
						),
						"exchange_gain_loss": flt(d.get("exchange_gain_loss")),
					}
				)
				lst.append(args)

		if lst:
			from erpnext.accounts.utils import reconcile_against_document

			# pass dimension values to utility method
			active_dimensions = get_dimensions()[0]
			for x in lst:
				for dim in active_dimensions:
					if self.get(dim.fieldname):
						x.update({dim.fieldname: self.get(dim.fieldname)})
			reconcile_against_document(lst, active_dimensions=active_dimensions)

	def cancel_system_generated_credit_debit_notes(self):
		# Cancel 'Credit/Debit' Note Journal Entries, if found.
		if self.doctype in ["Sales Invoice", "Purchase Invoice"]:
			voucher_type = "Credit Note" if self.doctype == "Sales Invoice" else "Debit Note"
			journals = frappe.db.get_all(
				"Journal Entry",
				filters={
					"is_system_generated": 1,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"voucher_type": voucher_type,
					"docstatus": 1,
				},
				pluck="name",
			)
			for x in journals:
				frappe.get_doc("Journal Entry", x).cancel()

	def on_cancel(self):
		from erpnext.accounts.doctype.bank_transaction.bank_transaction import (
			remove_from_bank_transaction,
		)
		from erpnext.accounts.utils import (
			cancel_common_party_journal,
			cancel_exchange_gain_loss_journal,
			unlink_ref_doc_from_payment_entries,
		)

		remove_from_bank_transaction(self.doctype, self.name)

		if self.doctype in ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]:
			self.cancel_system_generated_credit_debit_notes()

			# Cancel Exchange Gain/Loss Journal before unlinking
			cancel_exchange_gain_loss_journal(self)
			cancel_common_party_journal(self)

			if frappe.db.get_single_value("Accounts Settings", "unlink_payment_on_cancellation_of_invoice"):
				unlink_ref_doc_from_payment_entries(self)

		elif self.doctype in ["Sales Order", "Purchase Order"]:
			if frappe.db.get_single_value(
				"Accounts Settings", "unlink_advance_payment_on_cancelation_of_order"
			):
				unlink_ref_doc_from_payment_entries(self)

			if self.doctype == "Sales Order":
				self.unlink_ref_doc_from_po()

	def unlink_ref_doc_from_po(self):
		so_items = []
		for item in self.items:
			so_items.append(item.name)

		linked_po = list(
			set(
				frappe.get_all(
					"Purchase Order Item",
					filters={
						"sales_order": self.name,
						"sales_order_item": ["in", so_items],
						"docstatus": ["<", 2],
					},
					pluck="parent",
				)
			)
		)

		if linked_po:
			frappe.db.set_value(
				"Purchase Order Item",
				{"sales_order": self.name, "sales_order_item": ["in", so_items], "docstatus": ["<", 2]},
				{"sales_order": None, "sales_order_item": None},
			)

			frappe.msgprint(_("Purchase Orders {0} are un-linked").format("\n".join(linked_po)))

	def get_tax_map(self):
		tax_map = {}
		for tax in self.get("taxes"):
			tax_map.setdefault(tax.account_head, 0.0)
			tax_map[tax.account_head] += tax.tax_amount

		return tax_map

	def get_amount_and_base_amount(self, item, enable_discount_accounting):
		amount = item.net_amount
		base_amount = item.base_net_amount

		if (
			enable_discount_accounting
			and self.get("discount_amount")
			and self.get("additional_discount_account")
		):
			amount += item.distributed_discount_amount
			base_amount += flt(
				item.distributed_discount_amount * self.get("conversion_rate"),
				item.precision("distributed_discount_amount"),
			)

		return amount, base_amount

	def get_tax_amounts(self, tax, enable_discount_accounting):
		amount = tax.tax_amount_after_discount_amount
		base_amount = tax.base_tax_amount_after_discount_amount

		if (
			enable_discount_accounting
			and self.get("discount_amount")
			and self.get("additional_discount_account")
			and self.get("apply_discount_on") == "Grand Total"
		):
			amount = tax.tax_amount
			base_amount = tax.base_tax_amount

		return amount, base_amount

	def make_discount_gl_entries(self, gl_entries):
		if self.doctype == "Purchase Invoice":
			enable_discount_accounting = cint(
				frappe.db.get_single_value("Buying Settings", "enable_discount_accounting")
			)
		elif self.doctype == "Sales Invoice":
			enable_discount_accounting = cint(
				frappe.db.get_single_value("Selling Settings", "enable_discount_accounting")
			)

		if self.doctype == "Purchase Invoice":
			dr_or_cr = "credit"
			rev_dr_cr = "debit"
			supplier_or_customer = self.supplier

		else:
			dr_or_cr = "debit"
			rev_dr_cr = "credit"
			supplier_or_customer = self.customer

		if enable_discount_accounting:
			for item in self.get("items"):
				if item.get("discount_amount") and item.get("discount_account"):
					discount_amount = item.discount_amount * item.qty
					if self.doctype == "Purchase Invoice":
						income_or_expense_account = (
							item.expense_account
							if (not item.enable_deferred_expense or self.is_return)
							else item.deferred_expense_account
						)
					else:
						income_or_expense_account = (
							item.income_account
							if (not item.enable_deferred_revenue or self.is_return)
							else item.deferred_revenue_account
						)

					account_currency = get_account_currency(item.discount_account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": item.discount_account,
								"against": supplier_or_customer,
								dr_or_cr: flt(
									discount_amount * self.get("conversion_rate"),
									item.precision("discount_amount"),
								),
								dr_or_cr + "_in_account_currency": flt(
									discount_amount, item.precision("discount_amount")
								),
								"cost_center": item.cost_center,
								"project": item.project,
							},
							account_currency,
							item=item,
						)
					)

					account_currency = get_account_currency(income_or_expense_account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": income_or_expense_account,
								"against": supplier_or_customer,
								rev_dr_cr: flt(
									discount_amount * self.get("conversion_rate"),
									item.precision("discount_amount"),
								),
								rev_dr_cr + "_in_account_currency": flt(
									discount_amount, item.precision("discount_amount")
								),
								"cost_center": item.cost_center,
								"project": item.project or self.project,
							},
							account_currency,
							item=item,
						)
					)

		if (
			(enable_discount_accounting or self.get("is_cash_or_non_trade_discount"))
			and self.get("additional_discount_account")
			and self.get("discount_amount")
		):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.additional_discount_account,
						"against": supplier_or_customer,
						dr_or_cr: self.base_discount_amount,
						"cost_center": self.cost_center or erpnext.get_default_cost_center(self.company),
					},
					item=self,
				)
			)

	def validate_multiple_billing(self, ref_dt, item_ref_dn, based_on):
		from erpnext.controllers.status_updater import get_allowance_for

		item_allowance = {}
		global_qty_allowance, global_amount_allowance = None, None

		role_allowed_to_over_bill = frappe.get_cached_value(
			"Accounts Settings", None, "role_allowed_to_over_bill"
		)
		user_roles = frappe.get_roles()

		total_overbilled_amt = 0.0

		reference_names = [d.get(item_ref_dn) for d in self.get("items") if d.get(item_ref_dn)]
		reference_details = self.get_billing_reference_details(reference_names, ref_dt + " Item", based_on)

		for item in self.get("items"):
			if not item.get(item_ref_dn):
				continue

			ref_amt = flt(reference_details.get(item.get(item_ref_dn)), self.precision(based_on, item))

			if not ref_amt:
				frappe.msgprint(
					_("System will not check over billing since amount for Item {0} in {1} is zero").format(
						item.item_code, ref_dt
					),
					title=_("Warning"),
					indicator="orange",
				)
				continue

			already_billed = self.get_billed_amount_for_item(item, item_ref_dn, based_on)

			total_billed_amt = flt(
				flt(already_billed) + flt(item.get(based_on)), self.precision(based_on, item)
			)

			allowance, item_allowance, global_qty_allowance, global_amount_allowance = get_allowance_for(
				item.item_code, item_allowance, global_qty_allowance, global_amount_allowance, "amount"
			)

			max_allowed_amt = flt(ref_amt * (100 + allowance) / 100)

			if total_billed_amt < 0 and max_allowed_amt < 0:
				# while making debit note against purchase return entry(purchase receipt) getting overbill error
				total_billed_amt = abs(total_billed_amt)
				max_allowed_amt = abs(max_allowed_amt)

			overbill_amt = total_billed_amt - max_allowed_amt
			total_overbilled_amt += overbill_amt

			if overbill_amt > 0.01 and role_allowed_to_over_bill not in user_roles:
				if self.doctype != "Purchase Invoice":
					self.throw_overbill_exception(item, max_allowed_amt)
				elif not cint(
					frappe.db.get_single_value(
						"Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"
					)
				):
					self.throw_overbill_exception(item, max_allowed_amt)

		if role_allowed_to_over_bill in user_roles and total_overbilled_amt > 0.1:
			frappe.msgprint(
				_("Overbilling of {} ignored because you have {} role.").format(
					total_overbilled_amt, role_allowed_to_over_bill
				),
				indicator="orange",
				alert=True,
			)

	def get_billing_reference_details(self, reference_names, reference_doctype, based_on):
		return frappe._dict(
			frappe.get_all(
				reference_doctype,
				filters={"name": ("in", reference_names)},
				fields=["name", based_on],
				as_list=1,
			)
		)

	def get_billed_amount_for_item(self, item, item_ref_dn, based_on):
		"""
		Returns Sum of Amount of
		Sales/Purchase Invoice Items
		that are linked to `item_ref_dn` (`dn_detail` / `pr_detail`)
		that are submitted OR not submitted but are under current invoice
		"""

		from frappe.query_builder import Criterion
		from frappe.query_builder.functions import Sum

		item_doctype = frappe.qb.DocType(item.doctype)
		based_on_field = frappe.qb.Field(based_on)
		join_field = frappe.qb.Field(item_ref_dn)

		result = (
			frappe.qb.from_(item_doctype)
			.select(Sum(based_on_field))
			.where(join_field == item.get(item_ref_dn))
			.where(
				Criterion.any(
					[  # select all items from other invoices OR current invoices
						Criterion.all(
							[  # for selecting items from other invoices
								item_doctype.docstatus == 1,
								item_doctype.parent != self.name,
							]
						),
						Criterion.all(
							[  # for selecting items from current invoice, that are linked to same reference
								item_doctype.docstatus == 0,
								item_doctype.parent == self.name,
								item_doctype.name != item.name,
							]
						),
					]
				)
			)
		).run()

		return result[0][0] if result else 0

	def throw_overbill_exception(self, item, max_allowed_amt):
		frappe.throw(
			_(
				"Cannot overbill for Item {0} in row {1} more than {2}. To allow over-billing, please set allowance in Accounts Settings"
			).format(item.item_code, item.idx, max_allowed_amt)
		)

	def get_company_default(self, fieldname, ignore_validation=False):
		from erpnext.accounts.utils import get_company_default

		return get_company_default(self.company, fieldname, ignore_validation=ignore_validation)

	def get_stock_items(self):
		stock_items = []
		item_codes = list(set(item.item_code for item in self.get("items")))
		if item_codes:
			stock_items = frappe.db.get_values(
				"Item", {"name": ["in", item_codes], "is_stock_item": 1}, pluck="name", cache=True
			)

		return stock_items

	def set_total_advance_paid(self):
		ple = frappe.qb.DocType("Payment Ledger Entry")
		party = self.customer if self.doctype == "Sales Order" else self.supplier
		advance = (
			frappe.qb.from_(ple)
			.select(ple.account_currency, Abs(Sum(ple.amount_in_account_currency)).as_("amount"))
			.where(
				(ple.against_voucher_type == self.doctype)
				& (ple.against_voucher_no == self.name)
				& (ple.party == party)
				& (ple.delinked == 0)
				& (ple.company == self.company)
			)
			.run(as_dict=True)
		)

		if advance:
			advance = advance[0]

			advance_paid = flt(advance.amount, self.precision("advance_paid"))
			formatted_advance_paid = fmt_money(
				advance_paid, precision=self.precision("advance_paid"), currency=advance.account_currency
			)

			if advance.account_currency:
				frappe.db.set_value(
					self.doctype, self.name, "party_account_currency", advance.account_currency
				)

			if advance.account_currency == self.currency:
				order_total = self.get("rounded_total") or self.grand_total
				precision = "rounded_total" if self.get("rounded_total") else "grand_total"
			else:
				order_total = self.get("base_rounded_total") or self.base_grand_total
				precision = "base_rounded_total" if self.get("base_rounded_total") else "base_grand_total"

			formatted_order_total = fmt_money(
				order_total, precision=self.precision(precision), currency=advance.account_currency
			)

			if self.currency == self.company_currency and advance_paid > order_total:
				frappe.throw(
					_(
						"Total advance ({0}) against Order {1} cannot be greater than the Grand Total ({2})"
					).format(formatted_advance_paid, self.name, formatted_order_total)
				)

			self.db_set("advance_paid", advance_paid)

	@property
	def company_abbr(self):
		if not hasattr(self, "_abbr"):
			self._abbr = frappe.get_cached_value("Company", self.company, "abbr")

		return self._abbr

	def raise_missing_debit_credit_account_error(self, party_type, party):
		"""Raise an error if debit to/credit to account does not exist."""
		db_or_cr = (
			frappe.bold(_("Debit To")) if self.doctype == "Sales Invoice" else frappe.bold(_("Credit To"))
		)
		rec_or_pay = "Receivable" if self.doctype == "Sales Invoice" else "Payable"

		link_to_party = frappe.utils.get_link_to_form(party_type, party)
		link_to_company = frappe.utils.get_link_to_form("Company", self.company)

		message = _("{0} Account not found against Customer {1}.").format(db_or_cr, frappe.bold(party) or "")
		message += "<br>" + _("Please set one of the following:") + "<br>"
		message += (
			"<br><ul><li>"
			+ _("'Account' in the Accounting section of Customer {0}").format(link_to_party)
			+ "</li>"
		)
		message += (
			"<li>"
			+ _("'Default {0} Account' in Company {1}").format(rec_or_pay, link_to_company)
			+ "</li></ul>"
		)

		frappe.throw(message, title=_("Account Missing"), exc=AccountMissingError)

	def validate_party(self):
		party_type, party = self.get_party()
		validate_party_frozen_disabled(party_type, party)

	def get_party(self):
		party_type = None
		if self.doctype in ("Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
			party_type = "Customer"

		elif self.doctype in (
			"Supplier Quotation",
			"Purchase Order",
			"Purchase Receipt",
			"Purchase Invoice",
		):
			party_type = "Supplier"

		elif self.meta.get_field("customer"):
			party_type = "Customer"

		elif self.meta.get_field("supplier"):
			party_type = "Supplier"

		party = self.get(party_type.lower()) if party_type else None

		return party_type, party

	def validate_currency(self):
		if self.get("currency"):
			party_type, party = self.get_party()
			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

				if (
					party_account_currency
					and party_account_currency != self.company_currency
					and self.currency != party_account_currency
				):
					frappe.throw(
						_("Accounting Entry for {0}: {1} can only be made in currency: {2}").format(
							party_type, party, party_account_currency
						),
						InvalidCurrency,
					)

				# Note: not validating with gle account because we don't have the account
				# at quotation / sales order level and we shouldn't stop someone
				# from creating a sales invoice if sales order is already created

	def validate_party_account_currency(self):
		if self.doctype not in ("Sales Invoice", "Purchase Invoice"):
			return

		if self.is_opening == "Yes":
			return

		party_type, party = self.get_party()
		party_gle_currency = get_party_gle_currency(party_type, party, self.company)
		party_account = self.get("debit_to") if self.doctype == "Sales Invoice" else self.get("credit_to")
		party_account_currency = get_account_currency(party_account)
		allow_multi_currency_invoices_against_single_party_account = frappe.db.get_singles_value(
			"Accounts Settings", "allow_multi_currency_invoices_against_single_party_account"
		)

		if (
			not party_gle_currency
			and (party_account_currency != self.currency)
			and not allow_multi_currency_invoices_against_single_party_account
		):
			frappe.throw(
				_("Party Account {0} currency ({1}) and document currency ({2}) should be same").format(
					frappe.bold(party_account), party_account_currency, self.currency
				)
			)

	def delink_advance_entries(self, linked_doc_name):
		total_allocated_amount = 0
		for adv in self.advances:
			consider_for_total_advance = True
			if adv.reference_name == linked_doc_name:
				frappe.db.sql(
					f"""delete from `tab{self.doctype} Advance`
					where name = %s""",
					adv.name,
				)
				consider_for_total_advance = False

			if consider_for_total_advance:
				total_allocated_amount += flt(adv.allocated_amount, adv.precision("allocated_amount"))

		frappe.db.set_value(
			self.doctype, self.name, "total_advance", total_allocated_amount, update_modified=False
		)

	def group_similar_items(self):
		grouped_items = {}
		# to update serial number in print
		count = 0

		fields_to_group = frappe.get_hooks("fields_for_group_similar_items")
		fields_to_group = set(fields_to_group)

		for item in self.items:
			item_values = grouped_items.setdefault(item.item_code, defaultdict(int))

			for field in fields_to_group:
				item_values[field] += item.get(field, 0)

		duplicate_list = []
		for item in self.items:
			if item.item_code in grouped_items:
				count += 1

				for field in fields_to_group:
					item.set(field, grouped_items[item.item_code][field])

				if item.qty:
					item.rate = flt(flt(item.amount) / flt(item.qty), item.precision("rate"))
				else:
					item.rate = 0

				item.idx = count
				del grouped_items[item.item_code]
			else:
				duplicate_list.append(item)
		for item in duplicate_list:
			self.remove(item)

	def set_payment_schedule(self):
		if (self.doctype == "Sales Invoice" and self.is_pos) or self.get("is_opening") == "Yes":
			self.payment_terms_template = ""
			return

		party_account_currency = self.get("party_account_currency")
		if not party_account_currency:
			party_type, party = self.get_party()

			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

		posting_date = self.get("bill_date") or self.get("posting_date") or self.get("transaction_date")
		date = self.get("due_date")
		due_date = date or posting_date

		base_grand_total = self.get("base_rounded_total") or self.base_grand_total
		grand_total = self.get("rounded_total") or self.grand_total
		automatically_fetch_payment_terms = 0

		if self.doctype in ("Sales Invoice", "Purchase Invoice"):
			base_grand_total = base_grand_total - flt(self.base_write_off_amount)
			grand_total = grand_total - flt(self.write_off_amount)
			po_or_so, doctype, fieldname = self.get_order_details()
			automatically_fetch_payment_terms = cint(
				frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
			)

		if self.get("total_advance"):
			if party_account_currency == self.company_currency:
				base_grand_total -= self.get("total_advance")
				grand_total = flt(
					base_grand_total / self.get("conversion_rate"), self.precision("grand_total")
				)
			else:
				grand_total -= self.get("total_advance")
				base_grand_total = flt(
					grand_total * self.get("conversion_rate"), self.precision("base_grand_total")
				)

		if not self.get("payment_schedule"):
			if (
				self.doctype in ["Sales Invoice", "Purchase Invoice"]
				and automatically_fetch_payment_terms
				and self.linked_order_has_payment_terms(po_or_so, fieldname, doctype)
			):
				self.fetch_payment_terms_from_order(po_or_so, doctype)
				if self.get("payment_terms_template"):
					self.ignore_default_payment_terms_template = 1
			elif self.get("payment_terms_template"):
				data = get_payment_terms(
					self.payment_terms_template, posting_date, grand_total, base_grand_total
				)
				for item in data:
					self.append("payment_schedule", item)
			elif self.doctype not in ["Purchase Receipt"]:
				data = dict(
					due_date=due_date,
					invoice_portion=100,
					payment_amount=grand_total,
					base_payment_amount=base_grand_total,
				)
				self.append("payment_schedule", data)

		allocate_payment_based_on_payment_terms = frappe.db.get_value(
			"Payment Terms Template", self.payment_terms_template, "allocate_payment_based_on_payment_terms"
		)

		if not (
			automatically_fetch_payment_terms
			and allocate_payment_based_on_payment_terms
			and self.linked_order_has_payment_terms(po_or_so, fieldname, doctype)
		):
			for d in self.get("payment_schedule"):
				if d.invoice_portion:
					d.payment_amount = flt(
						grand_total * flt(d.invoice_portion) / 100, d.precision("payment_amount")
					)
					d.base_payment_amount = flt(
						base_grand_total * flt(d.invoice_portion) / 100, d.precision("base_payment_amount")
					)
					d.outstanding = d.payment_amount
				elif not d.invoice_portion:
					d.base_payment_amount = flt(
						d.payment_amount * self.get("conversion_rate"), d.precision("base_payment_amount")
					)
		else:
			self.fetch_payment_terms_from_order(po_or_so, doctype)
			self.ignore_default_payment_terms_template = 1

	def get_order_details(self):
		if self.doctype == "Sales Invoice":
			po_or_so = self.get("items")[0].get("sales_order")
			po_or_so_doctype = "Sales Order"
			po_or_so_doctype_name = "sales_order"

		else:
			po_or_so = self.get("items")[0].get("purchase_order")
			po_or_so_doctype = "Purchase Order"
			po_or_so_doctype_name = "purchase_order"

		return po_or_so, po_or_so_doctype, po_or_so_doctype_name

	def linked_order_has_payment_terms(self, po_or_so, fieldname, doctype):
		if po_or_so and self.all_items_have_same_po_or_so(po_or_so, fieldname):
			if self.linked_order_has_payment_terms_template(po_or_so, doctype):
				return True
			elif self.linked_order_has_payment_schedule(po_or_so):
				return True

		return False

	def all_items_have_same_po_or_so(self, po_or_so, fieldname):
		for item in self.get("items"):
			if item.get(fieldname) != po_or_so:
				return False

		return True

	def linked_order_has_payment_terms_template(self, po_or_so, doctype):
		return frappe.get_value(doctype, po_or_so, "payment_terms_template")

	def linked_order_has_payment_schedule(self, po_or_so):
		return frappe.get_all("Payment Schedule", filters={"parent": po_or_so})

	def fetch_payment_terms_from_order(self, po_or_so, po_or_so_doctype):
		"""
		Fetch Payment Terms from Purchase/Sales Order on creating a new Purchase/Sales Invoice.
		"""
		po_or_so = frappe.get_cached_doc(po_or_so_doctype, po_or_so)

		self.payment_schedule = []
		self.payment_terms_template = po_or_so.payment_terms_template

		for schedule in po_or_so.payment_schedule:
			payment_schedule = {
				"payment_term": schedule.payment_term,
				"due_date": schedule.due_date,
				"invoice_portion": schedule.invoice_portion,
				"mode_of_payment": schedule.mode_of_payment,
				"description": schedule.description,
				"payment_amount": schedule.payment_amount,
				"base_payment_amount": schedule.base_payment_amount,
				"outstanding": schedule.outstanding,
				"paid_amount": schedule.paid_amount,
			}

			if schedule.discount_type == "Percentage":
				payment_schedule["discount_type"] = schedule.discount_type
				payment_schedule["discount"] = schedule.discount

			if not schedule.invoice_portion:
				payment_schedule["payment_amount"] = schedule.payment_amount

			self.append("payment_schedule", payment_schedule)

	def set_due_date(self):
		due_dates = [d.due_date for d in self.get("payment_schedule") if d.due_date]
		if due_dates:
			self.due_date = max(due_dates)

	def validate_payment_schedule_dates(self):
		dates = []
		li = []

		if self.doctype == "Sales Invoice" and self.is_pos:
			return

		for d in self.get("payment_schedule"):
			if self.doctype == "Sales Order" and getdate(d.due_date) < getdate(self.transaction_date):
				frappe.throw(
					_("Row {0}: Due Date in the Payment Terms table cannot be before Posting Date").format(
						d.idx
					)
				)
			elif d.due_date in dates:
				li.append(_("{0} in row {1}").format(d.due_date, d.idx))
			dates.append(d.due_date)

		if li:
			duplicates = "<br>" + "<br>".join(li)
			frappe.throw(_("Rows with duplicate due dates in other rows were found: {0}").format(duplicates))

	def validate_payment_schedule_amount(self):
		if (self.doctype == "Sales Invoice" and self.is_pos) or self.get("is_opening") == "Yes":
			return

		party_account_currency = self.get("party_account_currency")
		if not party_account_currency:
			party_type, party = self.get_party()

			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, self.company)

		if self.get("payment_schedule"):
			total = 0
			base_total = 0
			for d in self.get("payment_schedule"):
				total += flt(d.payment_amount, d.precision("payment_amount"))
				base_total += flt(d.base_payment_amount, d.precision("base_payment_amount"))

			base_grand_total = self.get("base_rounded_total") or self.base_grand_total
			grand_total = self.get("rounded_total") or self.grand_total

			if self.doctype in ("Sales Invoice", "Purchase Invoice"):
				base_grand_total = base_grand_total - flt(self.base_write_off_amount)
				grand_total = grand_total - flt(self.write_off_amount)

			if self.get("total_advance"):
				if party_account_currency == self.company_currency:
					base_grand_total -= self.get("total_advance")
					grand_total = flt(
						base_grand_total / self.get("conversion_rate"), self.precision("grand_total")
					)
				else:
					grand_total -= self.get("total_advance")
					base_grand_total = flt(
						grand_total * self.get("conversion_rate"), self.precision("base_grand_total")
					)

			if (
				flt(total, self.precision("grand_total")) - flt(grand_total, self.precision("grand_total"))
				> 0.1
				or flt(base_total, self.precision("base_grand_total"))
				- flt(base_grand_total, self.precision("base_grand_total"))
				> 0.1
			):
				frappe.throw(
					_("Total Payment Amount in Payment Schedule must be equal to Grand / Rounded Total")
				)

	def is_rounded_total_disabled(self):
		if self.meta.get_field("disable_rounded_total"):
			return self.disable_rounded_total
		else:
			return frappe.db.get_single_value("Global Defaults", "disable_rounded_total")

	def set_inter_company_account(self):
		"""
		Set intercompany account for inter warehouse transactions
		This account will be used in case billing company and internal customer's
		representation company is same
		"""

		if self.is_internal_transfer() and not self.unrealized_profit_loss_account:
			unrealized_profit_loss_account = frappe.get_cached_value(
				"Company", self.company, "unrealized_profit_loss_account"
			)

			if not unrealized_profit_loss_account:
				msg = _(
					"Please select Unrealized Profit / Loss account or add default Unrealized Profit / Loss account account for company {0}"
				).format(frappe.bold(self.company))
				frappe.throw(msg)

			self.unrealized_profit_loss_account = unrealized_profit_loss_account

	def is_internal_transfer(self):
		"""
		It will an internal transfer if its an internal customer and representation
		company is same as billing company
		"""
		if self.doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
			internal_party_field = "is_internal_customer"
		elif self.doctype in ("Purchase Invoice", "Purchase Receipt", "Purchase Order"):
			internal_party_field = "is_internal_supplier"
		else:
			return False

		if self.get(internal_party_field) and (self.represents_company == self.company):
			return True

		return False

	def process_common_party_accounting(self):
		is_invoice = self.doctype in ["Sales Invoice", "Purchase Invoice"]
		if not is_invoice:
			return

		if frappe.db.get_single_value("Accounts Settings", "enable_common_party_accounting"):
			party_link = self.get_common_party_link()
			if party_link and self.outstanding_amount:
				self.create_advance_and_reconcile(party_link)

	def get_common_party_link(self):
		party_type, party = self.get_party()
		return frappe.db.get_value(
			doctype="Party Link",
			filters={"secondary_role": party_type, "secondary_party": party},
			fieldname=["primary_role", "primary_party"],
			as_dict=True,
		)

	def create_advance_and_reconcile(self, party_link):
		secondary_party_type, secondary_party = self.get_party()
		primary_party_type, primary_party = party_link.primary_role, party_link.primary_party

		primary_account = get_party_account(primary_party_type, primary_party, self.company)
		secondary_account = get_party_account(secondary_party_type, secondary_party, self.company)
		primary_account_currency = get_account_currency(primary_account)
		secondary_account_currency = get_account_currency(secondary_account)

		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.posting_date = self.posting_date
		jv.company = self.company
		jv.remark = f"Adjustment for {self.doctype} {self.name}"
		jv.is_system_generated = True

		reconcilation_entry = frappe._dict()
		advance_entry = frappe._dict()

		reconcilation_entry.account = secondary_account
		reconcilation_entry.party_type = secondary_party_type
		reconcilation_entry.party = secondary_party
		reconcilation_entry.reference_type = self.doctype
		reconcilation_entry.reference_name = self.name
		reconcilation_entry.cost_center = self.cost_center or erpnext.get_default_cost_center(self.company)

		advance_entry.account = primary_account
		advance_entry.party_type = primary_party_type
		advance_entry.party = primary_party
		advance_entry.cost_center = self.cost_center or erpnext.get_default_cost_center(self.company)
		advance_entry.is_advance = "Yes"

		# update dimesions
		dimensions_dict = frappe._dict()
		active_dimensions = get_dimensions()[0]
		for dim in active_dimensions:
			dimensions_dict[dim.fieldname] = self.get(dim.fieldname)

		reconcilation_entry.update(dimensions_dict)
		advance_entry.update(dimensions_dict)

		if self.doctype == "Sales Invoice":
			reconcilation_entry.credit_in_account_currency = self.outstanding_amount
			advance_entry.debit_in_account_currency = self.outstanding_amount
		else:
			advance_entry.credit_in_account_currency = self.outstanding_amount
			reconcilation_entry.debit_in_account_currency = self.outstanding_amount

		default_currency = erpnext.get_company_currency(self.company)
		if primary_account_currency != default_currency or secondary_account_currency != default_currency:
			jv.multi_currency = 1

		jv.append("accounts", reconcilation_entry)
		jv.append("accounts", advance_entry)

		jv.save()
		jv.submit()

	def check_conversion_rate(self):
		default_currency = erpnext.get_company_currency(self.company)
		if not default_currency:
			throw(_("Please enter default currency in Company Master"))
		if (
			(self.currency == default_currency and flt(self.conversion_rate) != 1.00)
			or not self.conversion_rate
			or (self.currency != default_currency and flt(self.conversion_rate) == 1.00)
		):
			throw(_("Conversion rate cannot be 0 or 1"))

	def check_finance_books(self, item, asset):
		if (
			len(asset.finance_books) > 1
			and not item.get("finance_book")
			and not self.get("finance_book")
			and asset.finance_books[0].finance_book
		):
			frappe.throw(
				_("Select finance book for the item {0} at row {1}").format(item.item_code, item.idx)
			)

	def check_if_fields_updated(self, fields_to_check, child_tables):
		# Check if any field affecting accounting entry is altered
		doc_before_update = self.get_doc_before_save()
		accounting_dimensions = [*get_accounting_dimensions(), "cost_center", "project"]

		# Parent Level Accounts excluding party account
		fields_to_check += accounting_dimensions
		for field in fields_to_check:
			if doc_before_update.get(field) != self.get(field):
				return True

		# Check for child tables
		for table in child_tables:
			if check_if_child_table_updated(
				doc_before_update.get(table), self.get(table), child_tables[table]
			):
				return True

		return False

	@frappe.whitelist()
	def repost_accounting_entries(self):
		repost_ledger = frappe.new_doc("Repost Accounting Ledger")
		repost_ledger.company = self.company
		repost_ledger.append("vouchers", {"voucher_type": self.doctype, "voucher_no": self.name})
		repost_ledger.flags.ignore_permissions = True
		repost_ledger.insert()
		repost_ledger.submit()


@frappe.whitelist()
def get_tax_rate(account_head):
	return frappe.get_cached_value("Account", account_head, ["tax_rate", "account_name"], as_dict=True)


@frappe.whitelist()
def get_default_taxes_and_charges(master_doctype, tax_template=None, company=None):
	if not company:
		return {}

	if tax_template and company:
		tax_template_company = frappe.get_cached_value(master_doctype, tax_template, "company")
		if tax_template_company == company:
			return

	default_tax = frappe.db.get_value(master_doctype, {"is_default": 1, "company": company})

	return {
		"taxes_and_charges": default_tax,
		"taxes": get_taxes_and_charges(master_doctype, default_tax),
	}


@frappe.whitelist()
def get_taxes_and_charges(master_doctype, master_name):
	if not master_name:
		return
	from frappe.model import child_table_fields, default_fields

	tax_master = frappe.get_doc(master_doctype, master_name)

	taxes_and_charges = []
	for _i, tax in enumerate(tax_master.get("taxes")):
		tax = tax.as_dict()

		for fieldname in default_fields + child_table_fields:
			if fieldname in tax:
				del tax[fieldname]

		taxes_and_charges.append(tax)

	return taxes_and_charges


def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""

	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	if not conversion_rate:
		throw(
			_("{0} is mandatory. Maybe Currency Exchange record is not created for {1} to {2}.").format(
				conversion_rate_label, currency, company_currency
			)
		)


def validate_taxes_and_charges(tax):
	if tax.charge_type in ["Actual", "On Net Total", "On Paid Amount"] and tax.row_id:
		frappe.throw(
			_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'")
		)
	elif tax.charge_type in ["On Previous Row Amount", "On Previous Row Total"]:
		if cint(tax.idx) == 1:
			frappe.throw(
				_(
					"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
				)
			)
		elif not tax.row_id:
			frappe.throw(
				_("Please specify a valid Row ID for row {0} in table {1}").format(tax.idx, _(tax.doctype))
			)
		elif tax.row_id and cint(tax.row_id) >= cint(tax.idx):
			frappe.throw(
				_("Cannot refer row number greater than or equal to current row number for this Charge type")
			)

	if tax.charge_type == "Actual":
		tax.rate = None


def validate_account_head(idx, account, company, context=""):
	account_company = frappe.get_cached_value("Account", account, "company")
	is_group = frappe.get_cached_value("Account", account, "is_group")

	if account_company != company:
		frappe.throw(
			_("Row {0}: {3} Account {1} does not belong to Company {2}").format(
				idx, frappe.bold(account), frappe.bold(company), context
			),
			title=_("Invalid Account"),
		)

	if is_group:
		frappe.throw(
			_("Row {0}: Account {1} is a Group Account").format(idx, frappe.bold(account)),
			title=_("Invalid Account"),
		)


def validate_cost_center(tax, doc):
	if not tax.cost_center:
		return

	company = frappe.get_cached_value("Cost Center", tax.cost_center, "company")

	if company != doc.company:
		frappe.throw(
			_("Row {0}: Cost Center {1} does not belong to Company {2}").format(
				tax.idx, frappe.bold(tax.cost_center), frappe.bold(doc.company)
			),
			title=_("Invalid Cost Center"),
		)


def validate_inclusive_tax(tax, doc):
	def _on_previous_row_error(row_range):
		throw(
			_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(
				tax.idx, row_range
			)
		)

	if cint(getattr(tax, "included_in_print_rate", None)):
		if tax.charge_type == "Actual":
			# inclusive tax cannot be of type Actual
			throw(
				_("Charge of type 'Actual' in row {0} cannot be included in Item Rate or Paid Amount").format(
					tax.idx
				)
			)
		elif tax.charge_type == "On Previous Row Amount" and not cint(
			doc.get("taxes")[cint(tax.row_id) - 1].included_in_print_rate
		):
			# referred row should also be inclusive
			_on_previous_row_error(tax.row_id)
		elif tax.charge_type == "On Previous Row Total" and not all(
			[cint(t.included_in_print_rate) for t in doc.get("taxes")[: cint(tax.row_id) - 1]]
		):
			# all rows about the referred tax should be inclusive
			_on_previous_row_error("1 - %d" % (tax.row_id,))
		elif tax.get("category") == "Valuation":
			frappe.throw(_("Valuation type charges can not be marked as Inclusive"))


def set_balance_in_account_currency(
	gl_dict, account_currency=None, conversion_rate=None, company_currency=None
):
	if (not conversion_rate) and (account_currency != company_currency):
		frappe.throw(
			_("Account: {0} with currency: {1} can not be selected").format(gl_dict.account, account_currency)
		)

	gl_dict["account_currency"] = (
		company_currency if account_currency == company_currency else account_currency
	)

	# set debit/credit in account currency if not provided
	if flt(gl_dict.debit) and not flt(gl_dict.debit_in_account_currency):
		gl_dict.debit_in_account_currency = (
			gl_dict.debit if account_currency == company_currency else flt(gl_dict.debit / conversion_rate, 2)
		)

	if flt(gl_dict.credit) and not flt(gl_dict.credit_in_account_currency):
		gl_dict.credit_in_account_currency = (
			gl_dict.credit
			if account_currency == company_currency
			else flt(gl_dict.credit / conversion_rate, 2)
		)


def get_advance_journal_entries(
	party_type,
	party,
	party_account,
	amount_field,
	order_doctype,
	order_list,
	include_unallocated=True,
):
	journal_entry = frappe.qb.DocType("Journal Entry")
	journal_acc = frappe.qb.DocType("Journal Entry Account")
	q = (
		frappe.qb.from_(journal_entry)
		.inner_join(journal_acc)
		.on(journal_entry.name == journal_acc.parent)
		.select(
			ConstantColumn("Journal Entry").as_("reference_type"),
			(journal_entry.name).as_("reference_name"),
			(journal_entry.remark).as_("remarks"),
			(journal_acc[amount_field]).as_("amount"),
			(journal_acc.name).as_("reference_row"),
			(journal_acc.reference_name).as_("against_order"),
			(journal_acc.exchange_rate),
		)
		.where(
			journal_acc.account.isin(party_account)
			& (journal_acc.party_type == party_type)
			& (journal_acc.party == party)
			& (journal_acc.is_advance == "Yes")
			& (journal_entry.docstatus == 1)
		)
	)
	if party_type == "Customer":
		q = q.where(journal_acc.credit_in_account_currency > 0)

	else:
		q = q.where(journal_acc.debit_in_account_currency > 0)

	reference_or_condition = []

	if include_unallocated:
		reference_or_condition.append(journal_acc.reference_name.isnull())
		reference_or_condition.append(journal_acc.reference_name == "")

	if order_list:
		reference_or_condition.append(
			(journal_acc.reference_type == order_doctype) & ((journal_acc.reference_name).isin(order_list))
		)

	if reference_or_condition:
		q = q.where(Criterion.any(reference_or_condition))

	q = q.orderby(journal_entry.posting_date)

	journal_entries = q.run(as_dict=True)
	return list(journal_entries)


@erpnext.allow_regional
def get_advance_payment_entries_for_regional(*args, **kwargs):
	return get_advance_payment_entries(*args, **kwargs)


def get_advance_payment_entries(
	party_type,
	party,
	party_account,
	order_doctype,
	order_list=None,
	include_unallocated=True,
	against_all_orders=False,
	limit=None,
	condition=None,
):
	payment_entries = []
	payment_entry = frappe.qb.DocType("Payment Entry")

	if order_list or against_all_orders:
		q = get_common_query(
			party_type,
			party,
			party_account,
			limit,
			condition,
		)
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = q.inner_join(payment_ref).on(payment_entry.name == payment_ref.parent)
		q = q.select(
			(payment_ref.allocated_amount).as_("amount"),
			(payment_ref.name).as_("reference_row"),
			(payment_ref.reference_name).as_("against_order"),
		)

		q = q.where(payment_ref.reference_doctype == order_doctype)
		if order_list:
			q = q.where(payment_ref.reference_name.isin(order_list))

		allocated = list(q.run(as_dict=True))
		payment_entries += allocated
	if include_unallocated:
		q = get_common_query(
			party_type,
			party,
			party_account,
			limit,
			condition,
		)
		q = q.select((payment_entry.unallocated_amount).as_("amount"))
		q = q.where(payment_entry.unallocated_amount > 0)

		unallocated = list(q.run(as_dict=True))
		payment_entries += unallocated
	return payment_entries


def get_common_query(
	party_type,
	party,
	party_account,
	limit,
	condition,
):
	account_type = frappe.db.get_value("Party Type", party_type, "account_type")
	payment_type = "Receive" if account_type == "Receivable" else "Pay"
	payment_entry = frappe.qb.DocType("Payment Entry")

	q = (
		frappe.qb.from_(payment_entry)
		.select(
			ConstantColumn("Payment Entry").as_("reference_type"),
			(payment_entry.name).as_("reference_name"),
			payment_entry.posting_date,
			(payment_entry.remarks).as_("remarks"),
		)
		.where(payment_entry.payment_type == payment_type)
		.where(payment_entry.party_type == party_type)
		.where(payment_entry.party == party)
		.where(payment_entry.docstatus == 1)
	)

	if payment_type == "Receive":
		q = q.select((payment_entry.paid_from_account_currency).as_("currency"))
		q = q.select(payment_entry.paid_from)
		q = q.where(payment_entry.paid_from.isin(party_account))
	else:
		q = q.select((payment_entry.paid_to_account_currency).as_("currency"))
		q = q.select(payment_entry.paid_to)
		q = q.where(payment_entry.paid_to.isin(party_account))

	if payment_type == "Receive":
		q = q.select((payment_entry.source_exchange_rate).as_("exchange_rate"))
	else:
		q = q.select((payment_entry.target_exchange_rate).as_("exchange_rate"))

	if condition:
		# conditions should be built as an array and passed as Criterion
		common_filter_conditions = []

		common_filter_conditions.append(payment_entry.company == condition["company"])
		if condition.get("name", None):
			common_filter_conditions.append(payment_entry.name.like(f"%{condition.get('name')}%"))

		if condition.get("from_payment_date"):
			common_filter_conditions.append(payment_entry.posting_date.gte(condition["from_payment_date"]))

		if condition.get("to_payment_date"):
			common_filter_conditions.append(payment_entry.posting_date.lte(condition["to_payment_date"]))

		if condition.get("get_payments") is True:
			if condition.get("cost_center"):
				common_filter_conditions.append(payment_entry.cost_center == condition["cost_center"])

			if condition.get("accounting_dimensions"):
				for field, val in condition.get("accounting_dimensions").items():
					common_filter_conditions.append(payment_entry[field] == val)

			if condition.get("minimum_payment_amount"):
				common_filter_conditions.append(
					payment_entry.unallocated_amount.gte(condition["minimum_payment_amount"])
				)

			if condition.get("maximum_payment_amount"):
				common_filter_conditions.append(
					payment_entry.unallocated_amount.lte(condition["maximum_payment_amount"])
				)
		q = q.where(Criterion.all(common_filter_conditions))

	q = q.orderby(payment_entry.posting_date)
	q = q.limit(limit) if limit else q

	return q


def update_invoice_status():
	"""Updates status as Overdue for applicable invoices. Runs daily."""
	today = getdate()
	payment_schedule = frappe.qb.DocType("Payment Schedule")
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		invoice = frappe.qb.DocType(doctype)

		consider_base_amount = invoice.party_account_currency != invoice.currency
		payment_amount = (
			frappe.qb.terms.Case()
			.when(consider_base_amount, payment_schedule.base_payment_amount)
			.else_(payment_schedule.payment_amount)
		)

		payable_amount = (
			frappe.qb.from_(payment_schedule)
			.select(Sum(payment_amount))
			.where((payment_schedule.parent == invoice.name) & (payment_schedule.due_date < today))
		)

		total = (
			frappe.qb.terms.Case()
			.when(invoice.disable_rounded_total, invoice.grand_total)
			.else_(invoice.rounded_total)
		)

		base_total = (
			frappe.qb.terms.Case()
			.when(invoice.disable_rounded_total, invoice.base_grand_total)
			.else_(invoice.base_rounded_total)
		)

		total_amount = frappe.qb.terms.Case().when(consider_base_amount, base_total).else_(total)

		is_overdue = total_amount - invoice.outstanding_amount < payable_amount

		conditions = (
			(invoice.docstatus == 1)
			& (invoice.outstanding_amount > 0)
			& (invoice.status.like("Unpaid%") | invoice.status.like("Partly Paid%"))
			& (
				((invoice.is_pos & invoice.due_date < today) | is_overdue)
				if doctype == "Sales Invoice"
				else is_overdue
			)
		)

		status = (
			frappe.qb.terms.Case()
			.when(invoice.status.like("%Discounted"), "Overdue and Discounted")
			.else_("Overdue")
		)

		frappe.qb.update(invoice).set("status", status).where(conditions).run()


@frappe.whitelist()
def get_payment_terms(
	terms_template, posting_date=None, grand_total=None, base_grand_total=None, bill_date=None
):
	if not terms_template:
		return

	terms_doc = frappe.get_doc("Payment Terms Template", terms_template)

	schedule = []
	for d in terms_doc.get("terms"):
		term_details = get_payment_term_details(d, posting_date, grand_total, base_grand_total, bill_date)
		schedule.append(term_details)

	return schedule


@frappe.whitelist()
def get_payment_term_details(
	term, posting_date=None, grand_total=None, base_grand_total=None, bill_date=None
):
	term_details = frappe._dict()
	if isinstance(term, str):
		term = frappe.get_doc("Payment Term", term)
	else:
		term_details.payment_term = term.payment_term
	term_details.description = term.description
	term_details.invoice_portion = term.invoice_portion
	term_details.payment_amount = flt(term.invoice_portion) * flt(grand_total) / 100
	term_details.base_payment_amount = flt(term.invoice_portion) * flt(base_grand_total) / 100
	term_details.discount_type = term.discount_type
	term_details.discount = term.discount
	term_details.outstanding = term_details.payment_amount
	term_details.mode_of_payment = term.mode_of_payment

	if bill_date:
		term_details.due_date = get_due_date(term, bill_date)
		term_details.discount_date = get_discount_date(term, bill_date)
	elif posting_date:
		term_details.due_date = get_due_date(term, posting_date)
		term_details.discount_date = get_discount_date(term, posting_date)

	if getdate(term_details.due_date) < getdate(posting_date):
		term_details.due_date = posting_date

	return term_details


def get_due_date(term, posting_date=None, bill_date=None):
	due_date = None
	date = bill_date or posting_date
	if term.due_date_based_on == "Day(s) after invoice date":
		due_date = add_days(date, term.credit_days)
	elif term.due_date_based_on == "Day(s) after the end of the invoice month":
		due_date = add_days(get_last_day(date), term.credit_days)
	elif term.due_date_based_on == "Month(s) after the end of the invoice month":
		due_date = get_last_day(add_months(date, term.credit_months))
	return due_date


def get_discount_date(term, posting_date=None, bill_date=None):
	discount_validity = None
	date = bill_date or posting_date
	if term.discount_validity_based_on == "Day(s) after invoice date":
		discount_validity = add_days(date, term.discount_validity)
	elif term.discount_validity_based_on == "Day(s) after the end of the invoice month":
		discount_validity = add_days(get_last_day(date), term.discount_validity)
	elif term.discount_validity_based_on == "Month(s) after the end of the invoice month":
		discount_validity = get_last_day(add_months(date, term.discount_validity))
	return discount_validity


def get_supplier_block_status(party_name):
	"""
	Returns a dict containing the values of `on_hold`, `release_date` and `hold_type` of
	a `Supplier`
	"""
	supplier = frappe.get_doc("Supplier", party_name)
	info = {
		"on_hold": supplier.on_hold,
		"release_date": supplier.release_date,
		"hold_type": supplier.hold_type,
	}
	return info


def set_child_tax_template_and_map(item, child_item, parent_doc):
	args = {
		"item_code": item.item_code,
		"posting_date": parent_doc.transaction_date,
		"tax_category": parent_doc.get("tax_category"),
		"company": parent_doc.get("company"),
	}

	child_item.item_tax_template = _get_item_tax_template(args, item.taxes)
	if child_item.get("item_tax_template"):
		child_item.item_tax_rate = get_item_tax_map(
			parent_doc.get("company"), child_item.item_tax_template, as_json=True
		)


def add_taxes_from_tax_template(child_item, parent_doc, db_insert=True):
	add_taxes_from_item_tax_template = frappe.db.get_single_value(
		"Accounts Settings", "add_taxes_from_item_tax_template"
	)

	if child_item.get("item_tax_rate") and add_taxes_from_item_tax_template:
		tax_map = json.loads(child_item.get("item_tax_rate"))
		for tax_type in tax_map:
			tax_rate = flt(tax_map[tax_type])
			taxes = parent_doc.get("taxes") or []
			# add new row for tax head only if missing
			found = any(tax.account_head == tax_type for tax in taxes)
			if not found:
				tax_row = parent_doc.append("taxes", {})
				tax_row.update(
					{
						"description": str(tax_type).split(" - ")[0],
						"charge_type": "On Net Total",
						"account_head": tax_type,
						"rate": tax_rate,
					}
				)
				if parent_doc.doctype == "Purchase Order":
					tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
				if db_insert:
					tax_row.db_insert()


def set_order_defaults(parent_doctype, parent_doctype_name, child_doctype, child_docname, trans_item):
	"""
	Returns a Sales/Purchase Order Item child item containing the default values
	"""
	p_doc = frappe.get_doc(parent_doctype, parent_doctype_name)
	child_item = frappe.new_doc(child_doctype, parent_doc=p_doc, parentfield=child_docname)
	item = frappe.get_doc("Item", trans_item.get("item_code"))

	for field in ("item_code", "item_name", "description", "item_group"):
		child_item.update({field: item.get(field)})

	date_fieldname = "delivery_date" if child_doctype == "Sales Order Item" else "schedule_date"
	child_item.update({date_fieldname: trans_item.get(date_fieldname) or p_doc.get(date_fieldname)})
	child_item.stock_uom = item.stock_uom
	child_item.uom = trans_item.get("uom") or item.stock_uom
	child_item.warehouse = get_item_warehouse(item, p_doc, overwrite_warehouse=True)
	conversion_factor = flt(get_conversion_factor(item.item_code, child_item.uom).get("conversion_factor"))
	child_item.conversion_factor = flt(trans_item.get("conversion_factor")) or conversion_factor

	if child_doctype == "Purchase Order Item":
		# Initialized value will update in parent validation
		child_item.base_rate = 1
		child_item.base_amount = 1
	if child_doctype == "Sales Order Item":
		child_item.warehouse = get_item_warehouse(item, p_doc, overwrite_warehouse=True)
		if not child_item.warehouse:
			frappe.throw(
				_(
					"Cannot find a default warehouse for item {0}. Please set one in the Item Master or in Stock Settings."
				).format(frappe.bold(item.item_code))
			)

	set_child_tax_template_and_map(item, child_item, p_doc)
	add_taxes_from_tax_template(child_item, p_doc)
	return child_item


def validate_child_on_delete(row, parent):
	"""Check if partially transacted item (row) is being deleted."""
	if parent.doctype == "Sales Order":
		if flt(row.delivered_qty):
			frappe.throw(
				_("Row #{0}: Cannot delete item {1} which has already been delivered").format(
					row.idx, row.item_code
				)
			)
		if flt(row.work_order_qty):
			frappe.throw(
				_("Row #{0}: Cannot delete item {1} which has work order assigned to it.").format(
					row.idx, row.item_code
				)
			)
		if flt(row.ordered_qty):
			frappe.throw(
				_("Row #{0}: Cannot delete item {1} which is assigned to customer's purchase order.").format(
					row.idx, row.item_code
				)
			)

	if parent.doctype == "Purchase Order" and flt(row.received_qty):
		frappe.throw(
			_("Row #{0}: Cannot delete item {1} which has already been received").format(
				row.idx, row.item_code
			)
		)

	if flt(row.billed_amt):
		frappe.throw(
			_("Row #{0}: Cannot delete item {1} which has already been billed.").format(
				row.idx, row.item_code
			)
		)


def update_bin_on_delete(row, doctype):
	"""Update bin for deleted item (row)."""
	from erpnext.stock.stock_balance import (
		get_indented_qty,
		get_ordered_qty,
		get_reserved_qty,
		update_bin_qty,
	)

	qty_dict = {}

	if doctype == "Sales Order":
		qty_dict["reserved_qty"] = get_reserved_qty(row.item_code, row.warehouse)
	else:
		if row.material_request_item:
			qty_dict["indented_qty"] = get_indented_qty(row.item_code, row.warehouse)

		qty_dict["ordered_qty"] = get_ordered_qty(row.item_code, row.warehouse)

	if row.warehouse:
		update_bin_qty(row.item_code, row.warehouse, qty_dict)


def validate_and_delete_children(parent, data) -> bool:
	deleted_children = []
	updated_item_names = [d.get("docname") for d in data]
	for item in parent.items:
		if item.name not in updated_item_names:
			deleted_children.append(item)

	for d in deleted_children:
		validate_child_on_delete(d, parent)
		d.cancel()
		d.delete()

	if parent.doctype == "Purchase Order":
		parent.update_ordered_qty_in_so_for_removed_items(deleted_children)

	# need to update ordered qty in Material Request first
	# bin uses Material Request Items to recalculate & update
	parent.update_prevdoc_status()

	for d in deleted_children:
		update_bin_on_delete(d, parent.doctype)

	return bool(deleted_children)


@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
	def check_doc_permissions(doc, perm_type="create"):
		try:
			doc.check_permission(perm_type)
		except frappe.PermissionError:
			actions = {"create": "add", "write": "update"}

			frappe.throw(
				_("You do not have permissions to {} items in a {}.").format(
					actions[perm_type], parent_doctype
				),
				title=_("Insufficient Permissions"),
			)

	def validate_workflow_conditions(doc):
		workflow = get_workflow_name(doc.doctype)
		if not workflow:
			return

		workflow_doc = frappe.get_doc("Workflow", workflow)
		current_state = doc.get(workflow_doc.workflow_state_field)
		roles = frappe.get_roles()

		transitions = []
		for transition in workflow_doc.transitions:
			if transition.next_state == current_state and transition.allowed in roles:
				if not is_transition_condition_satisfied(transition, doc):
					continue
				transitions.append(transition.as_dict())

		if not transitions:
			frappe.throw(
				_("You are not allowed to update as per the conditions set in {} Workflow.").format(
					get_link_to_form("Workflow", workflow)
				),
				title=_("Insufficient Permissions"),
			)

	def get_new_child_item(item_row):
		child_doctype = "Sales Order Item" if parent_doctype == "Sales Order" else "Purchase Order Item"
		return set_order_defaults(parent_doctype, parent_doctype_name, child_doctype, child_docname, item_row)

	def validate_quantity(child_item, new_data):
		if not flt(new_data.get("qty")):
			frappe.throw(
				_("Row # {0}: Quantity for Item {1} cannot be zero").format(
					new_data.get("idx"), frappe.bold(new_data.get("item_code"))
				),
				title=_("Invalid Qty"),
			)

		if parent_doctype == "Sales Order" and flt(new_data.get("qty")) < flt(child_item.delivered_qty):
			frappe.throw(_("Cannot set quantity less than delivered quantity"))

		if parent_doctype == "Purchase Order" and flt(new_data.get("qty")) < flt(child_item.received_qty):
			frappe.throw(_("Cannot set quantity less than received quantity"))

	def should_update_supplied_items(doc) -> bool:
		"""Subcontracted PO can allow following changes *after submit*:

		1. Change rate of subcontracting - regardless of other changes.
		2. Change qty and/or add new items and/or remove items
		        Exception: Transfer/Consumption is already made, qty change not allowed.
		"""

		supplied_items_processed = any(
			item.supplied_qty or item.consumed_qty or item.returned_qty for item in doc.supplied_items
		)

		update_supplied_items = any_qty_changed or items_added_or_removed or any_conversion_factor_changed
		if update_supplied_items and supplied_items_processed:
			frappe.throw(_("Item qty can not be updated as raw materials are already processed."))

		return update_supplied_items

	def validate_fg_item_for_subcontracting(new_data, is_new):
		if is_new:
			if not new_data.get("fg_item"):
				frappe.throw(
					_("Finished Good Item is not specified for service item {0}").format(
						new_data["item_code"]
					)
				)
			else:
				is_sub_contracted_item, default_bom = frappe.db.get_value(
					"Item", new_data["fg_item"], ["is_sub_contracted_item", "default_bom"]
				)

				if not is_sub_contracted_item:
					frappe.throw(
						_("Finished Good Item {0} must be a sub-contracted item").format(new_data["fg_item"])
					)
				elif not default_bom:
					frappe.throw(_("Default BOM not found for FG Item {0}").format(new_data["fg_item"]))

		if not new_data.get("fg_item_qty"):
			frappe.throw(_("Finished Good Item {0} Qty can not be zero").format(new_data["fg_item"]))

	data = json.loads(trans_items)

	any_qty_changed = False  # updated to true if any item's qty changes
	items_added_or_removed = False  # updated to true if any new item is added or removed
	any_conversion_factor_changed = False

	parent = frappe.get_doc(parent_doctype, parent_doctype_name)

	check_doc_permissions(parent, "write")
	_removed_items = validate_and_delete_children(parent, data)
	items_added_or_removed |= _removed_items

	for d in data:
		new_child_flag = False

		if not d.get("item_code"):
			# ignore empty rows
			continue

		if not d.get("docname"):
			new_child_flag = True
			items_added_or_removed = True
			check_doc_permissions(parent, "create")
			child_item = get_new_child_item(d)
		else:
			check_doc_permissions(parent, "write")
			child_item = frappe.get_doc(parent_doctype + " Item", d.get("docname"))

			prev_rate, new_rate = flt(child_item.get("rate")), flt(d.get("rate"))
			prev_qty, new_qty = flt(child_item.get("qty")), flt(d.get("qty"))
			prev_fg_qty, new_fg_qty = flt(child_item.get("fg_item_qty")), flt(d.get("fg_item_qty"))
			prev_con_fac, new_con_fac = (
				flt(child_item.get("conversion_factor")),
				flt(d.get("conversion_factor")),
			)
			prev_uom, new_uom = child_item.get("uom"), d.get("uom")

			if parent_doctype == "Sales Order":
				prev_date, new_date = child_item.get("delivery_date"), d.get("delivery_date")
			elif parent_doctype == "Purchase Order":
				prev_date, new_date = child_item.get("schedule_date"), d.get("schedule_date")

			rate_unchanged = prev_rate == new_rate
			qty_unchanged = prev_qty == new_qty
			fg_qty_unchanged = prev_fg_qty == new_fg_qty
			uom_unchanged = prev_uom == new_uom
			conversion_factor_unchanged = prev_con_fac == new_con_fac
			any_conversion_factor_changed |= not conversion_factor_unchanged
			date_unchanged = (
				prev_date == getdate(new_date) if prev_date and new_date else False
			)  # in case of delivery note etc
			if (
				rate_unchanged
				and qty_unchanged
				and fg_qty_unchanged
				and conversion_factor_unchanged
				and uom_unchanged
				and date_unchanged
			):
				continue

		validate_quantity(child_item, d)
		if flt(child_item.get("qty")) != flt(d.get("qty")):
			any_qty_changed = True

		if (
			parent.doctype == "Purchase Order"
			and parent.is_subcontracted
			and not parent.is_old_subcontracting_flow
		):
			validate_fg_item_for_subcontracting(d, new_child_flag)
			child_item.fg_item_qty = flt(d["fg_item_qty"])

			if new_child_flag:
				child_item.fg_item = d["fg_item"]

		child_item.qty = flt(d.get("qty"))
		rate_precision = child_item.precision("rate") or 2
		conv_fac_precision = child_item.precision("conversion_factor") or 2
		qty_precision = child_item.precision("qty") or 2

		# Amount cannot be lesser than billed amount, except for negative amounts
		row_rate = flt(d.get("rate"), rate_precision)
		amount_below_billed_amt = flt(child_item.billed_amt, rate_precision) > flt(
			row_rate * flt(d.get("qty"), qty_precision), rate_precision
		)
		if amount_below_billed_amt and row_rate > 0.0:
			frappe.throw(
				_("Row #{0}: Cannot set Rate if amount is greater than billed amount for Item {1}.").format(
					child_item.idx, child_item.item_code
				)
			)
		else:
			child_item.rate = row_rate

		if d.get("conversion_factor"):
			if child_item.stock_uom == child_item.uom:
				child_item.conversion_factor = 1
			else:
				child_item.conversion_factor = flt(d.get("conversion_factor"), conv_fac_precision)

		if d.get("uom"):
			child_item.uom = d.get("uom")
			conversion_factor = flt(
				get_conversion_factor(child_item.item_code, child_item.uom).get("conversion_factor")
			)
			child_item.conversion_factor = (
				flt(d.get("conversion_factor"), conv_fac_precision) or conversion_factor
			)

		if d.get("delivery_date") and parent_doctype == "Sales Order":
			child_item.delivery_date = d.get("delivery_date")

		if d.get("schedule_date") and parent_doctype == "Purchase Order":
			child_item.schedule_date = d.get("schedule_date")

		if flt(child_item.price_list_rate):
			if flt(child_item.rate) > flt(child_item.price_list_rate):
				#  if rate is greater than price_list_rate, set margin
				#  or set discount
				child_item.discount_percentage = 0
				child_item.margin_type = "Amount"
				child_item.margin_rate_or_amount = flt(
					child_item.rate - child_item.price_list_rate,
					child_item.precision("margin_rate_or_amount"),
				)
				child_item.rate_with_margin = child_item.rate
			else:
				child_item.discount_percentage = flt(
					(1 - flt(child_item.rate) / flt(child_item.price_list_rate)) * 100.0,
					child_item.precision("discount_percentage"),
				)
				child_item.discount_amount = flt(child_item.price_list_rate) - flt(child_item.rate)
				child_item.margin_type = ""
				child_item.margin_rate_or_amount = 0
				child_item.rate_with_margin = 0

		child_item.flags.ignore_validate_update_after_submit = True
		if new_child_flag:
			parent.load_from_db()
			child_item.idx = len(parent.items) + 1
			child_item.insert()
		else:
			child_item.save()

	parent.reload()
	parent.flags.ignore_validate_update_after_submit = True
	parent.set_qty_as_per_stock_uom()
	parent.calculate_taxes_and_totals()
	parent.set_total_in_words()
	if parent_doctype == "Sales Order":
		make_packing_list(parent)
		parent.set_gross_profit()
	frappe.get_doc("Authorization Control").validate_approving_authority(
		parent.doctype, parent.company, parent.base_grand_total
	)

	parent.set_payment_schedule()
	if parent_doctype == "Purchase Order":
		parent.validate_minimum_order_qty()
		parent.validate_budget()
		if parent.is_against_so():
			parent.update_status_updater()
	else:
		parent.check_credit_limit()

	# reset index of child table
	for idx, row in enumerate(parent.get(child_docname), start=1):
		row.idx = idx

	parent.save()

	if parent_doctype == "Purchase Order":
		update_last_purchase_rate(parent, is_submit=1)

		if any_qty_changed or items_added_or_removed or any_conversion_factor_changed:
			parent.update_prevdoc_status()

		parent.update_requested_qty()
		parent.update_ordered_qty()
		parent.update_ordered_and_reserved_qty()
		parent.update_receiving_percentage()

		if parent.is_subcontracted:
			if parent.is_old_subcontracting_flow:
				if should_update_supplied_items(parent):
					parent.update_reserved_qty_for_subcontract()
					parent.create_raw_materials_supplied()
				parent.save()
			else:
				if not parent.can_update_items():
					frappe.throw(
						_(
							"Items cannot be updated as Subcontracting Order is created against the Purchase Order {0}."
						).format(frappe.bold(parent.name))
					)
	else:  # Sales Order
		parent.validate_warehouse()
		parent.update_reserved_qty()
		parent.update_project()
		parent.update_prevdoc_status("submit")
		parent.update_delivery_status()

	parent.reload()
	validate_workflow_conditions(parent)

	parent.update_blanket_order()
	parent.update_billing_percentage()
	parent.set_status()

	parent.validate_uom_is_integer("uom", "qty")
	parent.validate_uom_is_integer("stock_uom", "stock_qty")

	# Cancel and Recreate Stock Reservation Entries.
	if parent_doctype == "Sales Order":
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
			has_reserved_stock,
		)

		if has_reserved_stock(parent.doctype, parent.name):
			cancel_stock_reservation_entries(parent.doctype, parent.name)

			if parent.per_picked == 0:
				parent.create_stock_reservation_entries()


def check_if_child_table_updated(child_table_before_update, child_table_after_update, fields_to_check):
	fields_to_check = list(fields_to_check) + get_accounting_dimensions() + ["cost_center", "project"]

	# Check if any field affecting accounting entry is altered
	for index, item in enumerate(child_table_before_update):
		for field in fields_to_check:
			if child_table_after_update[index].get(field) != item.get(field):
				return True

	return False


def merge_taxes(source_taxes, target_doc):
	from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
		update_item_wise_tax_detail,
	)

	existing_taxes = target_doc.get("taxes") or []
	idx = 1
	for tax in source_taxes:
		found = False
		for t in existing_taxes:
			if t.account_head == tax.account_head and t.cost_center == tax.cost_center:
				t.tax_amount = flt(t.tax_amount) + flt(tax.tax_amount_after_discount_amount)
				t.base_tax_amount = flt(t.base_tax_amount) + flt(tax.base_tax_amount_after_discount_amount)
				update_item_wise_tax_detail(t, tax)
				found = True

		if not found:
			tax.charge_type = "Actual"
			tax.idx = idx
			idx += 1
			tax.included_in_print_rate = 0
			tax.dont_recompute_tax = 1
			tax.row_id = ""
			tax.tax_amount = tax.tax_amount_after_discount_amount
			tax.base_tax_amount = tax.base_tax_amount_after_discount_amount
			tax.item_wise_tax_detail = tax.item_wise_tax_detail
			existing_taxes.append(tax)

	target_doc.set("taxes", existing_taxes)


@erpnext.allow_regional
def validate_regional(doc):
	pass


@erpnext.allow_regional
def validate_einvoice_fields(doc):
	pass


@erpnext.allow_regional
def update_gl_dict_with_regional_fields(doc, gl_dict):
	pass
