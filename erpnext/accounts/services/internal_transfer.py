# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Internal transfer helpers: InternalTransferService for inter-company transaction validation and setup."""

import frappe
from frappe import _, bold
from frappe.utils import cint, flt


class InternalTransferService:
	"""Handles validation and setup for inter-company / internal transfer transactions."""

	def __init__(self, doc):
		self.doc = doc

	def is_internal_transfer(self) -> bool:
		"""Return True if document is an internal transfer (internal party + same represents_company)."""
		doc = self.doc
		if doc.doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
			internal_party_field = "is_internal_customer"
		elif doc.doctype in ("Purchase Invoice", "Purchase Receipt", "Purchase Order"):
			internal_party_field = "is_internal_supplier"
		else:
			return False

		return bool(doc.get(internal_party_field) and doc.represents_company == doc.company)

	def validate(self) -> None:
		"""Run all inter-company validations and apply internal-transfer field overrides."""
		self.validate_reference()
		self.validate_transaction()
		self.disable_pricing_rule()
		self.disable_tax_included_prices()

	def set_account(self) -> None:
		"""Set unrealized profit/loss account for internal transfers (SI/PI only)."""
		if not self.is_internal_transfer() or self.doc.unrealized_profit_loss_account:
			return

		unrealized_profit_loss_account = frappe.get_cached_value(
			"Company", self.doc.company, "unrealized_profit_loss_account"
		)

		if not unrealized_profit_loss_account:
			frappe.throw(
				_(
					"Please select Unrealized Profit / Loss account or add default Unrealized Profit / Loss account account for company {0}"
				).format(frappe.bold(self.doc.company))
			)

		self.doc.unrealized_profit_loss_account = unrealized_profit_loss_account

	def process_common_party_accounting(self) -> None:
		"""Auto-create and reconcile advance for common party links (called from on_submit)."""
		if self.doc.doctype not in ("Sales Invoice", "Purchase Invoice"):
			return

		if frappe.get_single_value("Accounts Settings", "enable_common_party_accounting"):
			party_link = self.get_common_party_link()
			if party_link and self.doc.outstanding_amount:
				from erpnext.accounts.services.advances import create_advance_and_reconcile

				create_advance_and_reconcile(self.doc, party_link)

	def get_common_party_link(self) -> frappe._dict | None:
		party_type, party = self.doc.get_party()
		return frappe.db.get_value(
			doctype="Party Link",
			filters={"secondary_role": party_type, "secondary_party": party},
			fieldname=["primary_role", "primary_party"],
			as_dict=True,
		)

	def validate_reference(self) -> None:
		if self.doc.get("is_return"):
			return
		if self.doc.doctype not in ("Purchase Invoice", "Purchase Receipt"):
			return
		if not self.is_internal_transfer():
			return

		if not (
			self.doc.get("inter_company_reference")
			or self.doc.get("inter_company_invoice_reference")
			or self.doc.get("inter_company_order_reference")
		):
			msg = _("Internal Sale or Delivery Reference missing.")
			msg += _("Please create purchase from internal sale or delivery document itself")
			frappe.throw(msg, title=_("Internal Sales Reference Missing"))

		label = "Delivery Note Item" if self.doc.doctype == "Purchase Receipt" else "Sales Invoice Item"
		field = frappe.scrub(label)

		for row in self.doc.get("items"):
			if not row.get(field):
				frappe.throw(
					_(f"At Row {row.idx}: The field {bold(label)} is mandatory for internal transfer"),
					title=_("Internal Transfer Reference Missing"),
				)

	def validate_transaction(self) -> None:
		if not cint(frappe.get_single_value("Accounts Settings", "maintain_same_internal_transaction_rate")):
			return

		applicable_doctypes = ("Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice")
		if self.doc.doctype not in applicable_doctypes:
			return
		if not (self.doc.get("is_internal_customer") or self.doc.get("is_internal_supplier")):
			return

		self._validate_transaction_by_voucher_type()

	def disable_pricing_rule(self) -> None:
		if not self.doc.get("ignore_pricing_rule") and self.is_internal_transfer():
			self.doc.ignore_pricing_rule = 1
			frappe.msgprint(
				_("Disabled pricing rules since this {} is an internal transfer").format(self.doc.doctype),
				alert=1,
			)

	def disable_tax_included_prices(self) -> None:
		if not self.is_internal_transfer():
			return

		tax_updated = False
		for tax in self.doc.get("taxes"):
			if tax.get("included_in_print_rate"):
				tax.included_in_print_rate = 0
				tax_updated = True

		if tax_updated:
			frappe.msgprint(
				_("Disabled tax included prices since this {} is an internal transfer").format(
					self.doc.doctype
				),
				alert=1,
			)

	def _validate_transaction_by_voucher_type(self) -> None:
		orders = ("Sales Order", "Purchase Order")
		invoices = ("Sales Invoice", "Purchase Invoice")

		if self.doc.doctype in orders and self.doc.get("inter_company_order_reference"):
			linked_doctype = "Sales Order" if self.doc.doctype == "Purchase Order" else "Purchase Order"
			self._validate_line_items(
				linked_doctype,
				"sales_order" if linked_doctype == "Sales Order" else "purchase_order",
				"sales_order_item" if linked_doctype == "Sales Order" else "purchase_order_item",
			)
		elif self.doc.doctype in invoices and self.doc.get("inter_company_invoice_reference"):
			linked_doctype = "Sales Invoice" if self.doc.doctype == "Purchase Invoice" else "Purchase Invoice"
			self._validate_line_items(
				linked_doctype,
				"sales_invoice" if linked_doctype == "Sales Invoice" else "purchase_invoice",
				"sales_invoice_item" if linked_doctype == "Sales Invoice" else "purchase_invoice_item",
			)

	def _validate_line_items(self, ref_dt: str, ref_dn_field: str, ref_link_field: str) -> None:
		action, role_allowed_to_override = frappe.get_cached_value(
			"Accounts Settings", "None", ["maintain_same_rate_action", "role_to_override_stop_action"]
		)

		reference_names = [d.get(ref_link_field) for d in self.doc.get("items") if d.get(ref_link_field)]
		reference_details = self.doc.get_reference_details(reference_names, ref_dt + " Item")

		stop_actions = []

		for d in self.doc.get("items"):
			if not d.get(ref_link_field):
				continue

			ref_rate = reference_details.get(d.get(ref_link_field))
			if ref_rate is None or abs(flt(d.rate - ref_rate, d.precision("rate"))) < 0.01:
				continue

			ref_name = (
				self.doc.inter_company_invoice_reference
				if d.parenttype in ("Sales Invoice", "Purchase Invoice")
				else d.get(ref_dn_field)
			)
			msg = _("Row #{0}: Rate must be same as {1}: {2} ({3} / {4})").format(
				d.idx, ref_dt, ref_name, d.rate, ref_rate
			)

			if action == "Stop":
				user_roles = frappe.get_all(
					"Has Role", filters={"parent": frappe.session.user}, fields=["role"], pluck="role"
				)
				if role_allowed_to_override not in user_roles:
					stop_actions.append(msg)
			else:
				frappe.msgprint(msg, title=_("Warning"), indicator="orange")

		if stop_actions:
			frappe.throw(stop_actions, as_list=True)
