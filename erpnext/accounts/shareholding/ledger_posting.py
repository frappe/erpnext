"""Shared ownership posting controls. Every caller participates in one DB transaction."""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from erpnext.accounts.shareholding.company_lock import lock_company


def validate_posting(company, share_class, posting_date):
	lock_company(company)
	date = getdate(posting_date)
	if date > getdate(nowdate()):
		frappe.throw(_("Future ownership postings are not allowed."))
	latest = frappe.db.get_value(
		"Share Ledger Entry",
		{"company": company, "share_class": share_class},
		"posting_date",
		order_by="posting_date desc, posting_sequence desc",
		for_update=True,
	)
	if latest and date < getdate(latest):
		frappe.throw(_("Post chronologically: this class already has movements dated {0}.").format(latest))


def assert_cancellable(source, reversal_date=None):
	"""Require dependent ownership operations to be reversed first."""
	lock_company(source.company)
	for entry in get_earliest_entries_by_class(source):
		checker = LaterMovementCheck(source, entry)
		if checker.has_unreversed_movement():
			frappe.throw(
				_(
					"Reverse later ownership movements affecting these share numbers before cancelling this document."
				)
			)
		if reversal_date and checker.has_reversal_after(reversal_date):
			frappe.throw(
				_("Cancellation would invalidate historical ownership before a later movement's reversal.")
			)
		validate_posting(source.company, entry.share_class, nowdate())


def get_earliest_entries_by_class(source):
	entries = frappe.get_all(
		"Share Ledger Entry",
		filters={"source_doctype": source.doctype, "source_name": source.name, "is_reversal": 0},
		fields=["name", "share_class", "posting_sequence", "from_share_number", "to_share_number"],
		order_by="posting_sequence asc",
	)
	earliest = {}
	for entry in entries:
		earliest.setdefault(entry.share_class, entry)
	return earliest.values()


class LaterMovementCheck:
	"""Find movements of the same share numbers posted after a source entry."""

	def __init__(self, source, entry):
		self.source = source
		self.entry = entry
		self.movement = frappe.qb.DocType("Share Ledger Entry")
		self.reversal = frappe.qb.DocType("Share Ledger Entry").as_("reversal")

	def has_unreversed_movement(self):
		query = (
			frappe.qb.from_(self.movement)
			.left_join(self.reversal)
			.on(self.reversal.reversal_of == self.movement.name)
			.select(self.movement.name)
			.where(self.get_later_movement_condition() & self.reversal.name.isnull())
			.limit(1)
		)
		return bool(query.run())

	def has_reversal_after(self, reversal_date):
		query = (
			frappe.qb.from_(self.movement)
			.join(self.reversal)
			.on(self.reversal.reversal_of == self.movement.name)
			.select(self.movement.name)
			.where(
				self.get_later_movement_condition()
				& (self.reversal.posting_date > self.movement.posting_date)
				& (self.reversal.posting_date > getdate(reversal_date))
			)
			.limit(1)
		)
		return bool(query.run())

	def get_later_movement_condition(self):
		movement, entry, source = self.movement, self.entry, self.source
		return (
			(movement.company == source.company)
			& (movement.share_class == entry.share_class)
			& (movement.from_share_number <= entry.to_share_number)
			& (movement.to_share_number >= entry.from_share_number)
			& (movement.posting_sequence > entry.posting_sequence)
			& ~((movement.source_doctype == source.doctype) & (movement.source_name == source.name))
			& (movement.is_reversal == 0)
		)
