# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name, get_workflow_state_field
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

WORKFLOW_DRAFT_STATES = ("Pending Approval", "Rejected")
ACCOUNT_FIELDS = (
	"investment_account",
	"accrued_interest_account",
	"interest_income_account",
	"dividend_income_account",
	"realised_gain_loss_account",
	"unrealised_gain_loss_account",
	"fair_value_adjustment_account",
	"tax_withheld_receivable_account",
	"charges_account",
)


class Investment(Document):
	def validate(self):
		self.set_default_accounts()
		self.validate_masters_are_active()
		self.validate_dates()
		self.validate_amounts()
		self.validate_company_links()
		self.validate_investment_renewal()
		self.set_status()

	def on_update(self):
		from erpnext.treasury.doctype.investment_renewal.investment_renewal import (
			update_new_investment,
		)

		update_new_investment(self)

	def before_submit(self):
		from erpnext.treasury.doctype.investment_renewal.investment_renewal import (
			validate_terms_change_reason,
		)

		validate_terms_change_reason(self)
		self.approved_by = frappe.session.user

	def on_cancel(self):
		from erpnext.treasury.doctype.investment_renewal.investment_renewal import (
			unlink_new_investment,
		)

		self.db_set("status", "Cancelled")
		unlink_new_investment(self)

	def on_trash(self):
		from erpnext.treasury.doctype.investment_renewal.investment_renewal import (
			unlink_new_investment,
		)

		unlink_new_investment(self)

	def set_default_accounts(self):
		"""Fill accounts left empty from the defaults in Investment Settings."""
		from erpnext.treasury.doctype.investment_settings.investment_settings import get_default_account

		for fieldname in ACCOUNT_FIELDS:
			if not self.get(fieldname):
				self.set(fieldname, get_default_account(self.company, fieldname))

		if not self.investment_account:
			frappe.throw(_("Please set the Investment Account, here or as a default in Investment Settings"))

	def validate_masters_are_active(self):
		if self.docstatus != 0:
			return

		for fieldname, doctype in (
			("investment_type", "Investment Type"),
			("issuer", "Financial Institution"),
			("custodian", "Financial Institution"),
		):
			name = self.get(fieldname)
			if name and not frappe.db.get_value(doctype, name, "is_active"):
				frappe.throw(_("{0} {1} is inactive").format(_(doctype), frappe.bold(name)))

	def validate_dates(self):
		if self.maturity_date and getdate(self.maturity_date) <= getdate(self.purchase_date):
			frappe.throw(_("Maturity Date must be after Purchase Date"))

	def validate_amounts(self):
		for fieldname in ("principal_amount", "face_value"):
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(fieldname))))

		if flt(self.approved_amount) <= 0:
			frappe.throw(_("Approved Amount must be greater than zero"))

	def validate_company_links(self):
		validate_company_links(self, ACCOUNT_FIELDS)
		validate_company_links(self, ("cost_center",), "Cost Center")

	def validate_investment_renewal(self):
		from erpnext.treasury.doctype.investment_renewal.investment_renewal import (
			validate_new_investment,
		)

		validate_new_investment(self)

	def set_status(self):
		if self.docstatus == 1:
			if self.status in ("Draft", *WORKFLOW_DRAFT_STATES):
				self.status = "Active"
			return

		workflow_state = self.get_workflow_state()
		self.status = workflow_state if workflow_state in WORKFLOW_DRAFT_STATES else "Draft"

	def get_workflow_state(self):
		workflow_name = get_workflow_name(self.doctype)
		if not workflow_name:
			return None

		return self.get(get_workflow_state_field(workflow_name))

	def update_position(self):
		"""Recompute position totals from the ledger; called on transaction submit/cancel."""
		total_cost = self.get_ledger_balance(self.investment_account)
		units_held = self.get_units_held()
		values = {
			"total_cost": total_cost,
			"accrued_interest": self.get_ledger_balance(self.accrued_interest_account),
			"units_held": units_held,
			"market_value": total_cost + flt(self.unrealised_gain_loss),
			"unamortised_premium_discount": self.get_unamortised_premium_discount(units_held),
			"status": self.get_position_status(total_cost),
		}
		self.db_set(values)

	def get_ledger_balance(self, account, upto=None):
		if not account:
			return 0

		from erpnext.treasury.ledger import get_investment_gl_query

		ledger = get_investment_gl_query()
		gl_entry = ledger.gl_entry
		query = (
			ledger.query.select(Sum(gl_entry.debit) - Sum(gl_entry.credit))
			.where(gl_entry.account == account)
			.where(gl_entry.is_cancelled == 0)
			.where(ledger.investment == self.name)
		)
		if upto:
			query = query.where(gl_entry.posting_date <= upto)

		balance = query.run()

		return flt(balance[0][0], self.precision("total_cost"))

	def get_unamortised_premium_discount(self, units_held):
		"""Face value still held minus its book value, both in the investment currency: positive is
		discount, negative is premium."""
		if self.instrument_class != "Bond":
			return 0

		return flt(
			units_held * flt(self.face_value) - self.get_book_value_in_investment_currency(),
			self.precision("unamortised_premium_discount"),
		)

	def get_book_value_in_investment_currency(self, upto=None, exclude=None):
		"""Purchases - exits + amortisation, in the investment currency (the ledger is in company currency)."""
		from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
			EXIT_TYPES,
			get_purchases,
			get_submitted_sum,
		)

		purchased = sum(
			flt(purchase.amount)
			for purchase in get_purchases(self.name)
			if not upto or getdate(purchase.posting_date) <= getdate(upto)
		)
		exited = get_submitted_sum(
			"Investment Transaction", "cost_of_units_sold", self.name, upto, exclude, EXIT_TYPES
		)
		amortised = get_submitted_sum("Investment Interest Accrual", "amortisation_amount", self.name, upto)

		return purchased - exited + amortised

	def get_units_held(self):
		from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
			UNIT_CLASSES,
			get_units_held,
		)

		return get_units_held(self.name) if self.instrument_class in UNIT_CLASSES else 0

	def get_position_status(self, total_cost):
		from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
			get_exit_transactions,
		)

		exit_types = {t.transaction_type for t in get_exit_transactions(self.name)}

		if not exit_types:
			return "Active"

		if total_cost > 0:
			return "Partially Redeemed"

		return "Matured" if "Maturity" in exit_types else "Redeemed"

	def set_interest_schedule(self, rows, accrued_upto):
		"""Replace the Interest Schedule rows of this submitted investment; see interest_schedule.py."""
		frappe.db.delete(
			"Investment Interest Schedule",
			{"parent": self.name, "parenttype": self.doctype, "parentfield": "interest_schedule"},
		)
		self.set("interest_schedule", rows)
		for row in self.interest_schedule:
			row.db_insert()

		self.db_set("accrued_upto", accrued_upto)

	def update_revaluation(self):
		"""Take the figures of the latest submitted Investment Revaluations; called on revaluation submit/cancel."""
		from erpnext.treasury.doctype.investment_revaluation.investment_revaluation import (
			get_latest_revaluation_row,
		)

		latest_row = get_latest_revaluation_row(self.name)
		unrealised_gain_loss = flt(latest_row.unrealised_gain_loss) if latest_row else 0

		self.db_set(
			{
				"unrealised_gain_loss": unrealised_gain_loss,
				"market_value": flt(self.total_cost) + unrealised_gain_loss,
			}
		)

	def get_account(self, fieldname):
		"""Account set on this investment, else the Investment Settings default (saved on the investment)."""
		from erpnext.treasury.doctype.investment_settings.investment_settings import get_default_account

		account = self.get(fieldname)
		if not account and (account := get_default_account(self.company, fieldname)):
			self.db_set(fieldname, account)

		if not account:
			frappe.throw(
				_("Please set {0} in Investment {1}").format(
					frappe.bold(_(self.meta.get_label(fieldname))), frappe.bold(self.name)
				)
			)

		return account


def validate_company_links(doc, fieldnames, doctype="Account"):
	"""Linked Accounts (or Cost Centers) must belong to the document's company."""
	for fieldname in fieldnames:
		value = doc.get(fieldname)
		if value and frappe.get_cached_value(doctype, value, "company") != doc.company:
			frappe.throw(
				_("{0} {1} does not belong to Company {2}").format(
					_(doc.meta.get_label(fieldname)), frappe.bold(value), frappe.bold(doc.company)
				)
			)
