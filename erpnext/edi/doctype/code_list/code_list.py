# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from lxml.etree import Element


class CodeList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		canonical_uri: DF.Data | None
		description: DF.SmallText | None
		publisher: DF.Data | None
		publisher_id: DF.Data | None
		title: DF.Data | None
		url: DF.Data | None
		version: DF.Data | None
	# end: auto-generated types

	def on_trash(self):
		if not frappe.flags.in_bulk_delete:
			self.__delete_linked_docs()

	def __delete_linked_docs(self):
		linked_docs = frappe.get_all(
			"Common Code",
			filters={"code_list": self.name},
			fields=["name"],
		)

		for doc in linked_docs:
			frappe.delete_doc("Common Code", doc.name, force=1)

	def get_code_for(self, doctype: str, name: str):
		"""Get code for a doctype and name"""
		CommonCode = frappe.qb.DocType("Common Code")
		DynamicLink = frappe.qb.DocType("Dynamic Link")

		code = (
			frappe.qb.from_(CommonCode)
			.join(DynamicLink)
			.on((CommonCode.name == DynamicLink.parent) & (DynamicLink.parenttype == "Common Code"))
			.select(CommonCode.common_code)
			.where(
				(DynamicLink.link_doctype == doctype)
				& (DynamicLink.link_name == name)
				& (CommonCode.code_list == self.name)
			)
		).run()

		return code[0][0] if code else None

	def from_genericode(self, root: "Element"):
		"""Extract Code List details from genericode XML"""
		self.title = root.find(".//Identification/ShortName").text
		self.version = root.find(".//Identification/Version").text
		self.canonical_uri = root.find(".//CanonicalUri").text
		# optionals
		self.description = getattr(root.find(".//Identification/LongName"), "text", None)
		self.publisher = getattr(root.find(".//Identification/Agency/ShortName"), "text", None)
		if not self.publisher:
			self.publisher = getattr(root.find(".//Identification/Agency/LongName"), "text", None)
		self.publisher_id = getattr(root.find(".//Identification/Agency/Identifier"), "text", None)
		self.url = getattr(root.find(".//Identification/LocationUri"), "text", None)
