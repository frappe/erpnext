# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ShareClass(Document):
	def validate(self):
		if flt(self.votes_per_share) < 0 or flt(self.dividend_rate) < 0:
			frappe.throw(_("Votes and dividend rates cannot be negative."))
		self.validate_legacy_mapping()
		self.validate_posted_identity()

	def validate_legacy_mapping(self):
		if not self.legacy_share_type:
			return
		frappe.db.get_value("Share Type", self.legacy_share_type, "name", for_update=True)
		if frappe.db.exists(
			"Share Class",
			{"legacy_share_type": self.legacy_share_type, "name": ["!=", self.name]},
		):
			frappe.throw(_("This Legacy Share Type is already mapped to another Share Class."))

	def validate_posted_identity(self):
		previous = self.get_doc_before_save()
		if not previous or not frappe.db.exists("Share Ledger Entry", {"share_class": self.name}):
			return
		for field in ("class_code", "legacy_share_type"):
			if self.get(field) != previous.get(field):
				frappe.throw(
					_("{0} cannot be changed after shares have been posted.").format(
						_(self.meta.get_label(field))
					)
				)


def on_doctype_update():
	frappe.db.add_unique("Share Class", ["class_code"], constraint_name="unique_share_class_code")
