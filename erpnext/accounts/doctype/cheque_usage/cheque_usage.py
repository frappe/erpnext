# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now


class ChequeUsage(Document):
	def validate(self):
		frappe.throw(_("Cheque Usage is managed automatically"))

	def on_trash(self):
		frappe.throw(_("Cheque Usage is managed automatically"))


def on_doctype_update():
	frappe.db.add_unique("Cheque Usage", ["cheque_book", "cheque_no"])


def get_cheque_usage(cheque_book, cheque_no, *, for_update=False):
	return frappe.db.get_value(
		"Cheque Usage",
		f"{cheque_book}-{cheque_no}",
		["source_type", "source_name", "reason"],
		as_dict=True,
		for_update=for_update,
	)


def claim_cheque(book, cheque_no, source_type, source_name, reason=None):
	"""Called with the book locked; claims and source documents share one transaction."""
	usage = get_cheque_usage(book.name, cheque_no, for_update=True)
	if usage:
		if (usage.source_type, usage.source_name) != (source_type, source_name):
			frappe.throw(_("Cheque No {0} is already occupied by {1}").format(cheque_no, usage.source_name))
		frappe.db.set_value("Cheque Usage", f"{book.name}-{cheque_no}", "reason", reason)
	else:
		# Bypass user-facing lifecycle: only the source document's hooks maintain this table.
		frappe.get_doc(
			{
				"doctype": "Cheque Usage",
				"cheque_book": book.name,
				"cheque_no": cheque_no,
				"source_type": source_type,
				"source_name": source_name,
				"reason": reason,
			}
		).db_insert()
	# Every usage change writes the book, even for an out-of-sequence cheque. PostgreSQL
	# REPEATABLE READ then rejects stale transactions instead of letting them count old usage.
	frappe.db.set_value("Cheque Book", book.name, "modified", now())


def release_cheque(book, cheque_no, source_type, source_name):
	"""Called with the book locked; never releases a different document's claim."""
	frappe.db.delete(
		"Cheque Usage",
		{
			"cheque_book": book.name,
			"cheque_no": cheque_no,
			"source_type": source_type,
			"source_name": source_name,
		},
	)
	frappe.db.set_value("Cheque Book", book.name, "modified", now())
