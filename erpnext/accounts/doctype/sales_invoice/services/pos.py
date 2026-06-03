# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""POS helpers for Sales Invoice."""

import frappe
from frappe import _, msgprint
from frappe.utils import cint, flt, get_link_to_form


class PartialPaymentValidationError(frappe.ValidationError):
	pass


class POSService:
	def __init__(self, doc):
		self.doc = doc

	def set_pos_fields(self, for_validate: bool = False) -> frappe.Document | None:
		"""Populate POS-profile fields on the invoice; return the profile or None."""
		doc = self.doc
		if cint(doc.is_pos) != 1:
			return None

		if not doc.account_for_change_amount:
			doc.account_for_change_amount = frappe.get_cached_value(
				"Company", doc.company, "default_cash_account"
			)

		from erpnext.stock.get_item_details import (
			ItemDetailsCtx,
			get_pos_profile,
			get_pos_profile_item_details_,
		)

		if not doc.pos_profile and not doc.flags.ignore_pos_profile:
			pos_profile = get_pos_profile(doc.company) or {}
			if not pos_profile:
				return None
			doc.pos_profile = pos_profile.get("name")

		pos = {}
		if doc.pos_profile:
			pos = frappe.get_doc("POS Profile", doc.pos_profile)

		if pos:
			if not for_validate:
				update_multi_mode_option(doc, pos)
				doc.tax_category = pos.get("tax_category")

			if not for_validate and not doc.customer:
				doc.customer = pos.customer

			if not for_validate:
				doc.ignore_pricing_rule = pos.ignore_pricing_rule

			if pos.get("account_for_change_amount"):
				doc.account_for_change_amount = pos.get("account_for_change_amount")

			for fieldname in (
				"currency",
				"letter_head",
				"tc_name",
				"company",
				"select_print_heading",
				"write_off_account",
				"taxes_and_charges",
				"write_off_cost_center",
				"apply_discount_on",
				"cost_center",
			):
				if (not for_validate) or (for_validate and not doc.get(fieldname)):
					doc.set(fieldname, pos.get(fieldname))

			if pos.get("company_address"):
				doc.company_address = pos.get("company_address")

			if doc.customer:
				customer_price_list, customer_group = frappe.get_value(
					"Customer", doc.customer, ["default_price_list", "customer_group"]
				)
				customer_group_price_list = frappe.get_value(
					"Customer Group", customer_group, "default_price_list"
				)
				selling_price_list = (
					customer_price_list or customer_group_price_list or pos.get("selling_price_list")
				)
			else:
				selling_price_list = pos.get("selling_price_list")

			if selling_price_list:
				doc.set("selling_price_list", selling_price_list)

			if not for_validate:
				dn_flag = any(d.get("dn_detail") for d in doc.get("items"))
				doc.update_stock = 0 if dn_flag else cint(pos.get("update_stock"))

			for item in doc.get("items"):
				if item.get("item_code"):
					profile_details = get_pos_profile_item_details_(
						ItemDetailsCtx(item.as_dict()), pos, pos, update_data=True
					)
					for fname, val in profile_details.items():
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			if doc.tc_name and not doc.terms:
				doc.terms = frappe.db.get_value("Terms and Conditions", doc.tc_name, "terms")

			if doc.taxes_and_charges and not len(doc.get("taxes")):
				from erpnext.accounts.services.taxes import TaxService

				TaxService(doc).set_taxes()

		return pos

	def set_paid_amount(self) -> None:
		doc = self.doc
		paid_amount = 0.0
		base_paid_amount = 0.0
		for data in doc.payments:
			data.base_amount = flt(data.amount * doc.conversion_rate, doc.precision("base_paid_amount"))
			paid_amount += data.amount
			base_paid_amount += data.base_amount
		doc.paid_amount = paid_amount
		doc.base_paid_amount = base_paid_amount

	def set_account_for_mode_of_payment(self) -> None:
		for payment in self.doc.payments:
			payment.account = get_bank_cash_account(payment.mode_of_payment, self.doc.company).get("account")

	def reset_mode_of_payments(self) -> None:
		doc = self.doc
		if doc.pos_profile:
			pos_profile = frappe.get_cached_doc("POS Profile", doc.pos_profile)
			update_multi_mode_option(doc, pos_profile)
			doc.paid_amount = 0

	def validate_pos_return(self) -> None:
		doc = self.doc
		if doc.is_consolidated:
			return

		if doc.is_pos and doc.is_return:
			total_amount_in_payments = sum(payment.amount for payment in doc.payments)
			invoice_total = doc.rounded_total or doc.grand_total
			if total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}").format(-invoice_total))

	def validate_pos_paid_amount(self) -> None:
		doc = self.doc
		if len(doc.payments) == 0 and doc.is_pos and flt(doc.grand_total) > 0:
			frappe.throw(_("At least one mode of payment is required for POS invoice."))

	def validate_pos(self) -> None:
		doc = self.doc
		if doc.is_return:
			invoice_total = doc.rounded_total or doc.grand_total
			if abs(flt(doc.paid_amount)) + abs(flt(doc.write_off_amount)) - abs(flt(invoice_total)) > 1.0 / (
				10.0 ** (doc.precision("grand_total") + 1.0)
			):
				frappe.throw(_("Paid amount + Write Off Amount can not be greater than Grand Total"))

	def validate_created_using_pos(self) -> None:
		doc = self.doc
		if doc.is_created_using_pos and not doc.pos_profile:
			frappe.throw(_("POS Profile is mandatory to mark this invoice as POS Transaction."))

		doc.invoice_type_in_pos = frappe.db.get_single_value("POS Settings", "invoice_type")
		if doc.invoice_type_in_pos == "POS Invoice" and not doc.is_return:
			frappe.throw(_("Transactions using Sales Invoice in POS are disabled."))

		self.validate_pos_opening_entry()

	def validate_full_payment(self) -> None:
		doc = self.doc
		allow_partial_payment = frappe.db.get_value("POS Profile", doc.pos_profile, "allow_partial_payment")
		invoice_total = flt(doc.rounded_total) or flt(doc.grand_total)

		if (
			doc.docstatus == 1
			and not doc.is_return
			and not allow_partial_payment
			and doc.paid_amount < invoice_total
		):
			frappe.throw(
				msg=_("Partial Payment in POS Transactions are not allowed."),
				exc=PartialPaymentValidationError,
			)

	def validate_pos_opening_entry(self) -> None:
		doc = self.doc
		opening_entries = frappe.get_all(
			"POS Opening Entry",
			fields=["name", "period_start_date"],
			filters={"pos_profile": doc.pos_profile, "status": "Open"},
			order_by="period_start_date desc",
		)
		if not opening_entries:
			frappe.throw(
				title=_("POS Opening Entry Missing"),
				msg=_("No open POS Opening Entry found for POS Profile {0}.").format(
					frappe.bold(doc.pos_profile)
				),
			)
		if len(opening_entries) > 1:
			frappe.throw(
				title=_("Multiple POS Opening Entry"),
				msg=_(
					"POS Profile - {0} has multiple open POS Opening Entries. Please close or cancel the existing entries before proceeding."
				).format(doc.pos_profile),
			)
		if frappe.utils.get_date_str(opening_entries[0].get("period_start_date")) != frappe.utils.today():
			frappe.throw(
				title=_("Outdated POS Opening Entry"),
				msg=_(
					"POS Opening Entry - {0} is outdated. Please close the POS and create a new POS Opening Entry."
				).format(opening_entries[0].get("name")),
			)

	def check_if_consolidated_invoice(self) -> None:
		doc = self.doc
		if doc.doctype == "Sales Invoice" and doc.is_consolidated:
			invoice_or_credit_note = "consolidated_credit_note" if doc.is_return else "consolidated_invoice"
			pos_closing_entry = frappe.get_all(
				"POS Invoice Merge Log",
				filters={invoice_or_credit_note: doc.name},
				pluck="pos_closing_entry",
			)
			if pos_closing_entry and pos_closing_entry[0]:
				msg = _("To cancel a {} you need to cancel the POS Closing Entry {}.").format(
					frappe.bold(_("Consolidated Sales Invoice")),
					get_link_to_form("POS Closing Entry", pos_closing_entry[0]),
				)
				frappe.throw(msg, title=_("Not Allowed"))

	def check_if_created_using_pos_and_pos_closing_entry_generated(self) -> None:
		doc = self.doc
		if doc.doctype == "Sales Invoice" and doc.is_created_using_pos and doc.pos_closing_entry:
			pos_closing_entry_docstatus = frappe.db.get_value(
				"POS Closing Entry", doc.pos_closing_entry, "docstatus"
			)
			if pos_closing_entry_docstatus == 1:
				frappe.throw(
					msg=_(
						"To cancel this Sales Invoice you need to cancel the POS Closing Entry {0}."
					).format(get_link_to_form("POS Closing Entry", doc.pos_closing_entry)),
					title=_("Not Allowed"),
				)

	def cancel_pos_invoice_credit_note_generated_during_sales_invoice_mode(self) -> None:
		pos_invoices = frappe.get_all(
			"POS Invoice", filters={"consolidated_invoice": self.doc.name}, pluck="name"
		)
		for pos_invoice in pos_invoices:
			frappe.get_doc("POS Invoice", pos_invoice).cancel()

	def clear_unallocated_mode_of_payments(self) -> None:
		doc = self.doc
		doc.set("payments", doc.get("payments", {"amount": ["not in", [0, None, ""]]}))
		frappe.db.delete("Sales Invoice Payment", filters={"parent": doc.name, "amount": 0})

	def allow_write_off_only_on_pos(self) -> None:
		if not self.doc.is_pos and self.doc.write_off_account:
			self.doc.write_off_account = None

	def verify_payment_amount_is_positive(self) -> None:
		for entry in self.doc.payments:
			if entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))

	def verify_payment_amount_is_negative(self) -> None:
		for entry in self.doc.payments:
			if entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))

	def get_warehouse(self) -> str | None:
		doc = self.doc
		POSProfile = frappe.qb.DocType("POS Profile")

		user_query = (
			frappe.qb.from_(POSProfile)
			.select(POSProfile.name, POSProfile.warehouse)
			.where(POSProfile.company == doc.company)
			.where(
				(POSProfile.user == frappe.session["user"])
				| ((POSProfile.user.isnull() | (POSProfile.user == "")) & (frappe.session["user"] == ""))
			)
		)
		user_pos_profile = user_query.run()
		warehouse = user_pos_profile[0][1] if user_pos_profile else None

		if not warehouse:
			global_query = (
				frappe.qb.from_(POSProfile)
				.select(POSProfile.name, POSProfile.warehouse)
				.where(POSProfile.company == doc.company)
				.where(POSProfile.user.isnull() | (POSProfile.user == ""))
			)
			global_pos_profile = global_query.run()

			if global_pos_profile:
				warehouse = global_pos_profile[0][1]
			elif not user_pos_profile:
				msgprint(_("POS Profile required to make POS Entry"), raise_exception=True)

		return warehouse


def get_bank_cash_account(mode_of_payment: str, company: str) -> dict:
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": mode_of_payment, "company": company},
		"default_account",
	)
	if not account:
		frappe.throw(
			_("Please set default Cash or Bank account in Mode of Payment {0}").format(
				get_link_to_form("Mode of Payment", mode_of_payment)
			),
			title=_("Missing Account"),
		)
	return {"account": account}


def update_multi_mode_option(doc, pos_profile) -> None:
	def append_payment(payment_mode):
		payment = doc.append("payments", {})
		payment.default = payment_mode.default
		payment.mode_of_payment = payment_mode.mop
		payment.account = payment_mode.default_account
		payment.type = payment_mode.type

	mop_refetched = bool(doc.payments) and not doc.is_created_using_pos

	doc.set("payments", [])
	invalid_modes = []
	mode_of_payments = [d.mode_of_payment for d in pos_profile.get("payments")]
	mode_of_payments_info = get_mode_of_payments_info(mode_of_payments, doc.company)

	for row in pos_profile.get("payments"):
		payment_mode = mode_of_payments_info.get(row.mode_of_payment)
		if not payment_mode:
			invalid_modes.append(get_link_to_form("Mode of Payment", row.mode_of_payment))
			continue

		payment_mode.default = row.default
		append_payment(payment_mode)

	if invalid_modes:
		if invalid_modes == 1:
			msg = _("Please set default Cash or Bank account in Mode of Payment {}")
		else:
			msg = _("Please set default Cash or Bank account in Mode of Payments {}")
		frappe.throw(msg.format(", ".join(invalid_modes)), title=_("Missing Account"))

	if mop_refetched:
		frappe.toast(
			_("Payment methods refreshed. Please review before proceeding."),
			indicator="orange",
		)


def get_all_mode_of_payments(doc) -> list:
	ModeOfPaymentAccount = frappe.qb.DocType("Mode of Payment Account")
	ModeOfPayment = frappe.qb.DocType("Mode of Payment")

	query = (
		frappe.qb.from_(ModeOfPaymentAccount)
		.join(ModeOfPayment)
		.on(ModeOfPaymentAccount.parent == ModeOfPayment.name)
		.select(
			ModeOfPaymentAccount.default_account, ModeOfPaymentAccount.parent, ModeOfPayment.type.as_("type")
		)
		.where(ModeOfPaymentAccount.company == doc.company)
		.where(ModeOfPayment.enabled == 1)
	)

	return query.run(as_dict=1)


def get_mode_of_payments_info(mode_of_payments: list, company: str) -> dict:
	ModeOfPaymentAccount = frappe.qb.DocType("Mode of Payment Account")
	ModeOfPayment = frappe.qb.DocType("Mode of Payment")

	query = (
		frappe.qb.from_(ModeOfPaymentAccount)
		.join(ModeOfPayment)
		.on(ModeOfPaymentAccount.parent == ModeOfPayment.name)
		.select(
			ModeOfPaymentAccount.default_account,
			ModeOfPaymentAccount.parent.as_("mop"),
			ModeOfPayment.type.as_("type"),
		)
		.where(ModeOfPaymentAccount.company == company)
		.where(ModeOfPayment.enabled == 1)
		.where(ModeOfPayment.name.isin(mode_of_payments))
		.groupby(ModeOfPayment.name)
	)

	data = query.run(as_dict=1)

	return {row.get("mop"): row for row in data}


def get_mode_of_payment_info(mode_of_payment: str, company: str) -> list:
	ModeOfPaymentAccount = frappe.qb.DocType("Mode of Payment Account")
	ModeOfPayment = frappe.qb.DocType("Mode of Payment")

	query = (
		frappe.qb.from_(ModeOfPayment)
		.join(ModeOfPaymentAccount)
		.on(ModeOfPaymentAccount.parent == ModeOfPayment.name)
		.select(
			ModeOfPaymentAccount.default_account, ModeOfPaymentAccount.parent, ModeOfPayment.type.as_("type")
		)
		.where(ModeOfPaymentAccount.company == company)
		.where(ModeOfPayment.enabled == 1)
		.where(ModeOfPayment.name == mode_of_payment)
	)

	return query.run(as_dict=1)
