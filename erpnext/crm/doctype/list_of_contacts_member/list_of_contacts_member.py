# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ListofContactsMember(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contact: DF.Link | None
		contact_list: DF.Link | None
		unsubscribed: DF.Check
	# end: auto-generated types

	def after_delete(self):
		contact_list = frappe.get_doc("List of Contacts", self.contact_list)
		contact_list.update_total_members()

	def after_insert(self):
		contact_list = frappe.get_doc("List of Contacts", self.contact_list)
		contact_list.update_total_members()


def after_doctype_insert():
	frappe.db.add_unique("List of Contacts Member", ("contact_list", "contact"))
