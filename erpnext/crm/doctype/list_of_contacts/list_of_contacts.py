# Copyright (c) 2015, Frappe Technologies and contributors
# License: MIT. See LICENSE

import contextlib

import frappe
from frappe import _
from frappe.model.document import Document


class ListofContacts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		title: DF.Data
		total_members: DF.Int

	# end: auto-generated types
	def onload(self):
		singles = [d.name for d in frappe.get_all("DocType", "name", {"issingle": 1})]
		self.get("__onload").import_types = [
			{"value": d.parent, "label": f"{d.parent} ({d.label})"}
			for d in frappe.get_all("DocField", ("parent", "label"), {"options": "Contact"})
			if d.parent not in singles
		]

	def import_from(self, doctype):
		"""Extract Contacts from given doctype and add them to the current list"""
		meta = frappe.get_meta(doctype)
		contact_field = next(
			d.fieldname for d in meta.fields if d.fieldtype == "Link" and d.options == "Contact"
		)
		unsubscribed_field = "unsubscribed" if meta.get_field("unsubscribed") else None
		added = 0

		for doc in frappe.get_all(doctype, [contact_field, unsubscribed_field or "name"]):
			with contextlib.suppress(frappe.UniqueValidationError, frappe.InvalidEmailAddressError):
				if contact := doc.get(contact_field):
					frappe.get_doc(
						{
							"doctype": "List of Contacts Member",
							"contact_list": self.name,
							"contact": contact,
							"unsubscribed": doc.get(unsubscribed_field) if unsubscribed_field else 0,
						}
					).insert(ignore_permissions=True)
					added += 1

		frappe.msgprint(_("{0} contact added").format(added))

		return self.update_total_members()

	def update_total_members(self):
		self.total_members = self.get_total_members()
		self.db_update()
		return self.total_members

	def get_total_members(self):
		return frappe.db.count(
			"List of Contacts Member",
			filters={
				"contact_list": self.name,
			},
		)

	def on_trash(self):
		for d in frappe.get_all("List of Contacts Member", "name", {"contact_list": self.name}):
			frappe.delete_doc("List of Contacts Member", d.name)


@frappe.whitelist()
def import_from(name, doctype):
	nlist = frappe.get_doc("List of Contacts", name)
	if nlist.has_permission("write"):
		return nlist.import_from(doctype)


@frappe.whitelist()
def add_contacts(name, contact_list):
	if not isinstance(contact_list, list | tuple):
		contact_list = contact_list.replace(",", "\n").split("\n")

	count = 0
	for contact in contact_list:
		contact = contact.strip()

		if not frappe.db.get_value("List of Contacts Member", {"contact_list": name, "contact": contact}):
			frappe.get_doc(
				{"doctype": "List of Contacts Member", "contact_list": name, "contact": contact}
			).insert(ignore_permissions=frappe.flags.ignore_permissions)
			count += 1
		else:
			pass

	frappe.msgprint(_("{0} members added").format(count))

	return frappe.get_doc("List of Contacts", name).update_total_members()
