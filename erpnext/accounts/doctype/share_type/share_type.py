# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ShareType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.LongText | None
		title: DF.Data
	# end: auto-generated types

	def before_insert(self):
		self.throw_legacy_read_only()

	def validate(self):
		self.throw_legacy_read_only()

	def on_trash(self):
		self.throw_legacy_read_only()

	def throw_legacy_read_only(self):
		frappe.throw(_("Share Type is read-only. Create a Share Class instead."))
