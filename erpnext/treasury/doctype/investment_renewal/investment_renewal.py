# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cstr, date_diff, flt, getdate

from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	EXIT_TYPES,
	get_submitted_sum,
)
from erpnext.treasury.interest import INTEREST_CLASSES

RENEWAL_TYPES = {"Deposit": "Auto Renewal", "Units": "Switch Scheme", "Bond": "Reinvestment"}

# investment fields that make up the "terms" of an instrument, compared to set New Terms Changed
TERM_FIELDS = {
	"Deposit": ("rate_of_interest", "interest_payout_type", "compounding_frequency", "payout_frequency"),
	"Bond": ("coupon_rate", "coupon_frequency"),
	"Units": ("scheme_name",),
}


class InvestmentRenewal(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link
		currency: DF.Link
		instrument_class: DF.Data | None
		interest_renewed: DF.Currency
		naming_series: DF.Literal["INV-RENEW-.YYYY.-"]
		new_investment: DF.Link | None
		new_terms_changed: DF.Check
		original_investment: DF.Link
		principal_renewed: DF.Currency
		remarks: DF.SmallText | None
		renewal_date: DF.Date
		renewal_type: DF.Literal["", "Auto Renewal", "Switch Scheme", "Reinvestment"]
		terms_change_reason: DF.SmallText | None
		total_renewed: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_original_investment()
		self.set_renewal_type()
		self.validate_dates()
		self.validate_amounts()

	def before_submit(self):
		self.validate_available_proceeds()

	def on_submit(self):
		self.link_or_create_new_investment()

	def before_cancel(self):
		self.validate_new_investment_cancelled()

	def get_original_investment(self):
		if not getattr(self, "_original_investment", None):
			self._original_investment = frappe.get_doc("Investment", self.original_investment)

		return self._original_investment

	def validate_original_investment(self):
		if self.get_original_investment().docstatus != 1:
			frappe.throw(
				_("Original Investment {0} must be approved (submitted) before it can be renewed").format(
					frappe.bold(self.original_investment)
				)
			)

	def set_renewal_type(self):
		self.renewal_type = RENEWAL_TYPES.get(self.instrument_class)

		if self.instrument_class not in INTEREST_CLASSES:
			self.interest_renewed = 0

	def validate_dates(self):
		if getdate(self.renewal_date) < getdate(self.get_original_investment().purchase_date):
			frappe.throw(_("Renewal Date cannot be before the Original Investment's Purchase Date"))

	def validate_amounts(self):
		if flt(self.principal_renewed) <= 0:
			frappe.throw(_("Principal Renewed must be greater than zero"))

		if flt(self.interest_renewed) < 0:
			frappe.throw(_("Interest Renewed cannot be negative"))

		self.total_renewed = flt(
			flt(self.principal_renewed) + flt(self.interest_renewed),
			self.precision("total_renewed"),
		)

	def validate_available_proceeds(self):
		"""Only money the original investment actually paid out (and not already renewed) can be renewed."""
		for fieldname, transaction_types in (
			("principal_renewed", EXIT_TYPES),
			("interest_renewed", ("Interest Receipt",)),
		):
			available = self.get_paid_out(transaction_types) - self.get_already_renewed(fieldname)
			if flt(self.get(fieldname)) > flt(available, self.precision(fieldname)):
				frappe.throw(
					_("{0} cannot be more than {1}, paid out by {2} up to {3} and not yet renewed").format(
						_(self.meta.get_label(fieldname)),
						frappe.bold(frappe.format_value(max(available, 0), currency=self.currency)),
						frappe.bold(self.original_investment),
						frappe.bold(frappe.format_value(self.renewal_date, "Date")),
					)
				)

	def get_paid_out(self, transaction_types):
		return get_submitted_sum(
			"Investment Transaction",
			"net_amount",
			self.original_investment,
			self.renewal_date,
			transaction_types=transaction_types,
		)

	def get_already_renewed(self, fieldname):
		return get_submitted_sum(
			self.doctype,
			fieldname,
			self.original_investment,
			exclude=self.name,
			link_field="original_investment",
		)

	def link_or_create_new_investment(self):
		"""Create the draft new investment; after an amendment it amends the old renewal's cancelled one."""
		investment = make_new_investment(self.name)
		investment.amended_from = self.get_cancelled_new_investment()
		investment.insert()

		self.db_set(
			{
				"new_investment": investment.name,
				"new_terms_changed": has_new_terms(self.get_original_investment(), investment),
			}
		)
		frappe.msgprint(
			_("Draft Investment {0} created. Please review and submit it for approval.").format(
				frappe.get_desk_link("Investment", investment.name)
			),
			alert=True,
		)

	def get_cancelled_new_investment(self):
		"""Latest cancelled new investment of the renewal this one amends, if it was not amended already."""
		if not self.amended_from:
			return None

		cancelled = frappe.get_all(
			"Investment",
			filters={"investment_renewal": self.amended_from, "docstatus": 2},
			order_by="creation desc",
			pluck="name",
			limit=1,
		)
		if cancelled and not frappe.db.exists("Investment", {"amended_from": cancelled[0]}):
			return cancelled[0]

		return None

	def validate_new_investment_cancelled(self):
		"""The user decides what happens to the new investment, so a draft is never deleted silently."""
		if open_investment := frappe.db.get_value(
			"Investment", {"investment_renewal": self.name, "docstatus": ("<", 2)}
		):
			frappe.throw(
				_(
					"Cannot cancel this renewal because its new Investment {0} is still open. Delete {0} if it is a draft, or cancel it if it is submitted."
				).format(frappe.get_desk_link("Investment", open_investment))
			)

	def validate_can_create_new_investment(self, new_investment=None):
		if self.docstatus != 1:
			frappe.throw(
				_("Investment Renewal {0} must be submitted before its new investment is created").format(
					frappe.bold(self.name)
				)
			)

		filters = {"investment_renewal": self.name, "docstatus": ("<", 2)}
		if new_investment:
			filters["name"] = ("!=", new_investment)

		if existing := frappe.db.get_value("Investment", filters):
			frappe.throw(
				_("Investment {0} is already created for Investment Renewal {1}").format(
					frappe.get_desk_link("Investment", existing), frappe.bold(self.name)
				)
			)

	def get_new_investment_values(self):
		values = {
			"docstatus": 0,
			"purchase_date": self.renewal_date,
			"maturity_date": self.get_new_maturity_date(),
			"approved_amount": self.total_renewed,
			"investment_rationale": _("Renewed from Investment {0} via Investment Renewal {1}").format(
				self.original_investment, self.name
			),
			"instrument_id": None,
			"approval_reference": None,
		}

		if self.instrument_class == "Deposit":
			values["principal_amount"] = self.total_renewed

		return values

	def get_new_maturity_date(self):
		"""Keep the original tenure, counted from the renewal date."""
		original = self.get_original_investment()
		if not original.maturity_date:
			return None

		return add_days(self.renewal_date, date_diff(original.maturity_date, original.purchase_date))


@frappe.whitelist()
def make_new_investment(source_name: str):
	"""Unsaved copy of the original investment, re-dated and re-sized for the money being renewed."""
	renewal = frappe.get_doc("Investment Renewal", source_name)
	renewal.check_permission("read")
	renewal.validate_can_create_new_investment()

	new_investment = frappe.copy_doc(renewal.get_original_investment())
	new_investment.update(renewal.get_new_investment_values())
	new_investment.investment_renewal = renewal.name

	return new_investment


def validate_new_investment(new_investment):
	"""Called when an investment is validated: a renewal can be the source of only one live investment."""
	if new_investment.investment_renewal:
		renewal = frappe.get_doc("Investment Renewal", new_investment.investment_renewal)
		renewal.validate_can_create_new_investment(new_investment.name)


def update_new_investment(new_investment):
	"""Called when an investment is saved: link it to its renewal and flag the renewal if its terms were edited."""
	if not new_investment.investment_renewal:
		return

	original_investment = frappe.db.get_value(
		"Investment Renewal", new_investment.investment_renewal, "original_investment"
	)
	original = frappe.get_doc("Investment", original_investment)
	frappe.db.set_value(
		"Investment Renewal",
		new_investment.investment_renewal,
		{"new_investment": new_investment.name, "new_terms_changed": has_new_terms(original, new_investment)},
	)


def validate_terms_change_reason(new_investment):
	"""Called before an investment is submitted: a renewal whose terms were changed must say why."""
	if not new_investment.investment_renewal:
		return

	renewal = frappe.get_doc("Investment Renewal", new_investment.investment_renewal)
	if renewal.terms_change_reason or not has_new_terms(renewal.get_original_investment(), new_investment):
		return

	frappe.throw(
		_(
			"The terms of this investment differ from the original. Please enter the Reason for Change in Terms in Investment Renewal {0} first."
		).format(frappe.get_desk_link(renewal.doctype, renewal.name)),
		title=_("Reason Required"),
	)


def unlink_new_investment(new_investment):
	"""Called when an investment is cancelled or deleted, so its renewal can create another one."""
	frappe.db.set_value(
		"Investment Renewal",
		{"new_investment": new_investment.name},
		{"new_investment": None, "new_terms_changed": 0},
	)


def has_new_terms(original, new_investment):
	fieldnames = TERM_FIELDS.get(original.instrument_class, ())
	if any(cstr(original.get(f)) != cstr(new_investment.get(f)) for f in fieldnames):
		return 1

	return int(get_tenure(original) != get_tenure(new_investment))


def get_tenure(investment):
	if not investment.maturity_date:
		return None

	return date_diff(investment.maturity_date, investment.purchase_date)
