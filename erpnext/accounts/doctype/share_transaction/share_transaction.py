# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate

from erpnext.accounts.shareholding.entries import create_ledger_entry
from erpnext.accounts.shareholding.folios import get_or_create_folio
from erpnext.accounts.shareholding.ledger import assert_cancellable, lock_company, validate_posting
from erpnext.accounts.shareholding.legacy import assert_legacy_history_backfilled
from erpnext.accounts.shareholding.ranges import (
	get_face_value_per_share,
	range_has_coverage,
)
from erpnext.accounts.shareholding.transaction_accounting import TransactionAccounting

TRANSACTION_FOLIOS = {
	"Issue": (("to_folio", 1),),
	"Transfer": (("from_folio", -1), ("to_folio", 1)),
	"Buyback": (("from_folio", -1), ("to_folio", 1)),
	"Retirement": (("from_folio", -1),),
	"Reissue": (("from_folio", -1), ("to_folio", 1)),
}

ACCOUNTING_TRANSACTION_TYPES = {"Issue", "Buyback", "Retirement", "Reissue"}


class ShareTransaction(TransactionAccounting, Document):
	def validate(self):
		if self.docstatus == 0:
			self.payment_entry = None
		self.set_company_defaults()
		self.validate_share_class()
		self.calculate_quantities_and_values()
		self.set_display_accounting_values()
		self.set_accounting_defaults()

	def before_submit(self):
		lock_company(self.company)
		assert_legacy_history_backfilled(self.company)
		self.resolve_folios()
		self.lock_shareholders()
		validate_posting(self.company, self.share_class, self.posting_date)
		self.set_face_value()
		self.validate_ownership()
		self.calculate_accounting_values()
		self.validate_accounting()

	def on_submit(self):
		self.create_ledger_entries()
		self.rebuild_shareholder_holdings()
		if self.transaction_type in ACCOUNTING_TRANSACTION_TYPES:
			self.make_accounting_gl_entries()
			self.create_direct_payment_entry()

	def before_cancel(self):
		previous = self.get_doc_before_save()
		if not previous:
			frappe.throw(_("Reload the submitted Share Transaction before cancellation."))
		self.validate_unchanged_since_submit(previous)
		self.validate_cancellation_date()
		lock_company(self.company)
		self.lock_shareholders()
		assert_cancellable(self, self.get_reversal_date())
		self.assert_payment_entry_unreconciled()

	def validate_unchanged_since_submit(self, previous):
		for field, value in previous.get_valid_dict().items():
			if field not in {"modified", "modified_by", "docstatus"} and self.is_field_changed(field, value):
				frappe.throw(_("Submitted transaction fields cannot be changed during cancellation."))

	def is_field_changed(self, field, value):
		current = self.get(field)
		df = self.meta.get_field(field)
		if df and df.fieldtype in {"Currency", "Float", "Int", "Check"}:
			return flt(current) != flt(value)
		return frappe.utils.cstr(current or "") != frappe.utils.cstr(value or "")

	def validate_cancellation_date(self):
		from erpnext.accounts.utils import is_immutable_ledger_enabled

		if self.transaction_type == "Transfer" or not is_immutable_ledger_enabled():
			return
		date = frappe.utils.getdate(frappe.form_dict.get("posting_date") or nowdate())
		if date < frappe.utils.getdate(self.posting_date) or date > frappe.utils.getdate(nowdate()):
			frappe.throw(_("Cancellation date must be between the original posting date and today."))

	def on_cancel(self):
		if self.transaction_type in ACCOUNTING_TRANSACTION_TYPES:
			self.cancel_payment_entry()
			self.reverse_accounting_gl_entries()
		self.create_reversal_entries()
		self.rebuild_shareholder_holdings()

	def rebuild_shareholder_holdings(self):
		from erpnext.accounts.doctype.shareholder.shareholder import rebuild_current_holdings

		folios = [folio for folio in (self.from_folio, self.to_folio) if folio]
		if not folios:
			return
		shareholders = frappe.get_all(
			"Share Folio",
			filters={"name": ["in", folios], "is_treasury": 0},
			pluck="shareholder",
		)
		for shareholder in sorted({shareholder for shareholder in shareholders if shareholder}):
			rebuild_current_holdings(shareholder)

	def lock_shareholders(self):
		for shareholder in sorted({self.from_shareholder, self.to_shareholder} - {None, ""}):
			frappe.db.get_value("Shareholder", shareholder, "name", for_update=True)

	def set_company_defaults(self):
		if not self.company:
			return

		self.currency = frappe.db.get_value("Company", self.company, "default_currency")

	def validate_share_class(self):
		if self.share_class:
			frappe.get_doc("Share Class", self.share_class).check_permission("read")

	def calculate_quantities_and_values(self):
		if flt(self.rate_per_share) < 0:
			frappe.throw(_("Rate Per Share cannot be negative."))
		from_share_number = cint(self.from_share_number)
		to_share_number = cint(self.to_share_number)

		if from_share_number <= 0 or to_share_number <= 0:
			frappe.throw(_("Share numbers must be greater than zero."))
		if to_share_number < from_share_number:
			frappe.throw(_("To Share Number cannot be less than From Share Number."))

		self.number_of_shares = to_share_number - from_share_number + 1
		self.total_amount = self.money(flt(self.rate_per_share) * self.number_of_shares)

		if self.transaction_type in {"Issue", "Buyback", "Reissue"} and flt(self.rate_per_share) <= 0:
			frappe.throw(
				_("Rate Per Share must be greater than zero for a {0}.").format(self.transaction_type)
			)

	def resolve_folios(self):
		for shareholder in {self.from_shareholder, self.to_shareholder} - {None, ""}:
			frappe.get_doc("Shareholder", shareholder).check_permission("read")
		if self.transaction_type not in TRANSACTION_FOLIOS:
			frappe.throw(_("Unsupported transaction type {0}.").format(frappe.bold(self.transaction_type)))
		if self.transaction_type == "Transfer" and self.from_shareholder == self.to_shareholder:
			frappe.throw(_("From Shareholder and To Shareholder must be different."))

		used = {field for field, _direction in TRANSACTION_FOLIOS[self.transaction_type]}
		for folio_field in ("from_folio", "to_folio"):
			if folio_field in used:
				self.resolve_folio(folio_field)
			else:
				self.clear_folio(folio_field)

	def clear_folio(self, folio_field):
		self.set(folio_field, None)
		self.set(self.get_shareholder_field(folio_field), None)

	def resolve_folio(self, folio_field):
		shareholder_field = self.get_shareholder_field(folio_field)
		if self.is_treasury_side(folio_field):
			self.set(shareholder_field, None)
			self.set(folio_field, get_or_create_folio(self.company, is_treasury=True))
			return
		self.set(
			folio_field,
			get_or_create_folio(self.company, self.get(shareholder_field), self.posting_date),
		)

	def get_shareholder_field(self, folio_field):
		return folio_field.replace("folio", "shareholder")

	def is_treasury_side(self, folio_field):
		treasury_sides = {
			"Buyback": "to_folio",
			"Retirement": "from_folio",
			"Reissue": "from_folio",
		}
		return treasury_sides.get(self.transaction_type) == folio_field

	def set_face_value(self):
		if self.transaction_type == "Issue":
			if flt(self.face_value_per_share) <= 0:
				frappe.throw(_("Face Value Per Share must be greater than zero for an Issue."))

			existing_face_value = frappe.db.get_value(
				"Share Ledger Entry",
				{"company": self.company, "share_class": self.share_class, "face_value_per_share": [">", 0]},
				"face_value_per_share",
				order_by="posting_date asc, posting_sequence asc",
				for_update=True,
			)
			if existing_face_value is not None and flt(existing_face_value) != flt(self.face_value_per_share):
				frappe.throw(
					_("Face Value Per Share must remain {0} for this company and share class.").format(
						frappe.bold(existing_face_value)
					)
				)
			return

		self.face_value_per_share = get_face_value_per_share(
			company=self.company,
			share_class=self.share_class,
			share_folio=self.from_folio,
			from_share_number=self.from_share_number,
			to_share_number=self.to_share_number,
			allow_unknown=self.transaction_type != "Retirement",
		)

	def validate_ownership(self):
		if self.transaction_type == "Issue":
			if not range_has_coverage(
				self.company,
				self.share_class,
				self.from_share_number,
				self.to_share_number,
				expected_coverage=0,
			):
				frappe.throw(_("One or more share numbers in this range have already been issued."))
			return

		source_folio = self.from_folio
		if not range_has_coverage(
			self.company,
			self.share_class,
			self.from_share_number,
			self.to_share_number,
			expected_coverage=1,
			share_folio=source_folio,
		):
			frappe.throw(_("The source folio does not own the complete selected share range."))

	def create_ledger_entries(self):
		folios = {self.get(field) for field, _direction in TRANSACTION_FOLIOS[self.transaction_type]}
		treasury_folios = set(
			frappe.get_all(
				"Share Folio", filters={"name": ["in", list(folios)], "is_treasury": 1}, pluck="name"
			)
		)
		for folio_field, direction in TRANSACTION_FOLIOS[self.transaction_type]:
			share_folio = self.get(folio_field)
			treasury_cost_change = 0
			if share_folio in treasury_folios:
				if self.transaction_type == "Buyback":
					treasury_cost_change = flt(self.treasury_cost)
				elif self.transaction_type in {"Retirement", "Reissue"}:
					treasury_cost_change = -flt(self.treasury_cost)

			create_ledger_entry(
				transaction=self,
				share_folio=share_folio,
				quantity_change=direction * self.number_of_shares,
				posting_date=self.posting_date,
				treasury_cost_change=treasury_cost_change,
			)

	def create_reversal_entries(self):
		original_entries = frappe.get_all(
			"Share Ledger Entry",
			filters={"share_transaction": self.name, "is_reversal": 0},
			fields=[
				"name",
				"share_folio",
				"from_share_number",
				"to_share_number",
				"quantity_change",
				"currency",
				"face_value_per_share",
				"treasury_cost_change",
				"company",
				"share_class",
				"transaction_type",
				"capital_change",
				"posting_date",
			],
			order_by="posting_sequence asc",
		)

		if not original_entries:
			frappe.throw(_("No ledger entries were found to reverse for this transaction."))

		for original in original_entries:
			if frappe.db.exists("Share Ledger Entry", {"reversal_of": original.name}):
				continue
			create_ledger_entry(
				transaction=self,
				share_folio=original.share_folio,
				quantity_change=-original.quantity_change,
				posting_date=self.get_reversal_date(),
				treasury_cost_change=-flt(original.treasury_cost_change),
				is_reversal=True,
				reversal_of=original.name,
				original=original,
			)

	def get_reversal_date(self):
		from erpnext.accounts.utils import is_immutable_ledger_enabled

		if self.transaction_type == "Transfer":
			return nowdate()
		if is_immutable_ledger_enabled():
			return frappe.utils.getdate(frappe.form_dict.get("posting_date") or nowdate())
		return self.posting_date
