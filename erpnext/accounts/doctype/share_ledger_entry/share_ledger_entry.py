# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class ShareLedgerEntry(Document):
	def validate(self):
		self.validate_source()
		self.validate_quantity()
		self.validate_company_and_currency()
		self.validate_treasury_cost()
		self.validate_reversal_link()

	def validate_source(self):
		if not self.is_new():
			frappe.throw(_("Share Ledger Entries are immutable and cannot be edited."))
		legacy_import = self.flags.from_legacy_migration and self.source_doctype == "Share Transfer"
		if not (self.flags.from_share_transaction or legacy_import or frappe.flags.in_patch):
			frappe.throw(_("Share Ledger Entries can only be created by a Share Transaction."))

	def validate_quantity(self):
		if not cint(self.quantity_change):
			frappe.throw(_("Quantity Change cannot be zero."))
		expected_quantity = cint(self.to_share_number) - cint(self.from_share_number) + 1
		if (
			cint(self.from_share_number) <= 0
			or expected_quantity <= 0
			or abs(cint(self.quantity_change)) != expected_quantity
		):
			frappe.throw(_("Quantity Change must match the share number range."))

	def validate_company_and_currency(self):
		folio_company = frappe.db.get_value("Share Folio", self.share_folio, "company")
		if folio_company != self.company:
			frappe.throw(_("Ledger and folio must belong to the same company."))
		if self.currency != frappe.db.get_value("Company", self.company, "default_currency"):
			frappe.throw(_("Ledger currency must match the company currency."))

	def validate_treasury_cost(self):
		is_treasury = frappe.db.get_value("Share Folio", self.share_folio, "is_treasury")
		if not is_treasury and flt(self.treasury_cost_change):
			frappe.throw(_("Treasury Cost Change can only be posted against a treasury folio."))
		if not is_treasury or self.transaction_type not in {"Buyback", "Retirement", "Reissue"}:
			return
		if self.transaction_type == "Buyback" and not flt(self.treasury_cost_change):
			frappe.throw(_("Treasury Cost Change is required for a treasury movement."))
		if cint(self.quantity_change) * flt(self.treasury_cost_change) < 0:
			frappe.throw(_("Treasury Cost Change and Quantity Change must have the same sign."))

	def validate_reversal_link(self):
		if self.is_reversal and not self.reversal_of:
			frappe.throw(_("Reversal Of is required for a reversal entry."))
		if not self.is_reversal and self.reversal_of:
			frappe.throw(_("A normal ledger entry cannot reference Reversal Of."))

	def on_trash(self):
		if not frappe.flags.in_patch:
			frappe.throw(_("Share Ledger Entries are immutable and cannot be deleted."))


def on_doctype_update():
	frappe.db.add_index(
		"Share Ledger Entry",
		["company", "share_class", "posting_date", "posting_sequence"],
		"equity_position_lookup",
	)
	frappe.db.add_index("Share Ledger Entry", ["source_doctype", "source_name"], "equity_source_lookup")
	frappe.db.add_index("Share Ledger Entry", ["company", "posting_sequence"], "company_posting_sequence")
	frappe.db.add_index(
		"Share Ledger Entry",
		["company", "share_class", "from_share_number", "to_share_number"],
		"share_range_lookup",
	)
