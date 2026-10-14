"""Shared ownership posting controls. Every caller participates in one DB transaction."""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from erpnext.accounts.shareholding.locking import lock_company


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
	entries = frappe.get_all(
		"Share Ledger Entry",
		filters={"source_doctype": source.doctype, "source_name": source.name, "is_reversal": 0},
		fields=["name", "share_class", "creation"],
	)
	earliest_by_class = {}
	for entry in entries:
		current = earliest_by_class.get(entry.share_class)
		if current is None or entry.creation < current.creation:
			earliest_by_class[entry.share_class] = entry
	for entry in earliest_by_class.values():
		movement = frappe.qb.DocType("Share Ledger Entry")
		reversal = frappe.qb.DocType("Share Ledger Entry").as_("reversal")
		later = (
			frappe.qb.from_(movement)
			.left_join(reversal)
			.on(reversal.reversal_of == movement.name)
			.select(movement.name)
			.where(
				(movement.company == source.company)
				& (movement.share_class == entry.share_class)
				& (movement.creation > entry.creation)
				& ~((movement.source_doctype == source.doctype) & (movement.source_name == source.name))
				& (movement.is_reversal == 0)
				& reversal.name.isnull()
			)
			.limit(1)
		).run()
		if later:
			frappe.throw(
				_("Reverse later ownership movements in this class before cancelling this document.")
			)
		if reversal_date:
			incompatible_reversal = (
				frappe.qb.from_(movement)
				.join(reversal)
				.on(reversal.reversal_of == movement.name)
				.select(movement.name)
				.where(
					(movement.company == source.company)
					& (movement.share_class == entry.share_class)
					& (movement.creation > entry.creation)
					& ~((movement.source_doctype == source.doctype) & (movement.source_name == source.name))
					& (movement.is_reversal == 0)
					& (reversal.posting_date > movement.posting_date)
					& (reversal.posting_date > getdate(reversal_date))
				)
				.limit(1)
			).run()
			if incompatible_reversal:
				frappe.throw(
					_(
						"Cancellation would invalidate historical ownership before a later movement's reversal."
					)
				)
		validate_posting(source.company, entry.share_class, nowdate())
