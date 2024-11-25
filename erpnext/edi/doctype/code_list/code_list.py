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
		default_common_code: DF.Link | None
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
		self.db_set("default_common_code", None)

		linked_docs = frappe.get_all(
			"Common Code",
			filters={"code_list": self.name},
			fields=["name"],
		)

		for doc in linked_docs:
			frappe.delete_doc("Common Code", doc.name)

	def get_codes_for(self, doctype: str, name: str) -> tuple[str]:
		"""Get the applicable codes for a doctype and name"""
		return get_codes_for(self.name, doctype, name)

	def get_docnames_for(self, doctype: str, code: str) -> tuple[str]:
		"""Get the mapped docnames for a doctype and code"""
		return get_docnames_for(self.name, doctype, code)

	def get_default_code(self) -> str | None:
		"""Get the default common code for this code list"""
		return (
			frappe.db.get_value("Common Code", self.default_common_code, "common_code")
			if self.default_common_code
			else None
		)

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


def get_codes_for(code_list: str, doctype: str, name: str) -> tuple[str]:
	"""Return the common code for a given record"""
	CommonCode = frappe.qb.DocType("Common Code")
	DynamicLink = frappe.qb.DocType("Dynamic Link")

	codes = (
		frappe.qb.from_(CommonCode)
		.join(DynamicLink)
		.on((CommonCode.name == DynamicLink.parent) & (DynamicLink.parenttype == "Common Code"))
		.select(CommonCode.common_code)
		.where(
			(DynamicLink.link_doctype == doctype)
			& (DynamicLink.link_name == name)
			& (CommonCode.code_list == code_list)
		)
		.distinct()
		.orderby(CommonCode.common_code)
	).run()

	return tuple(c[0] for c in codes) if codes else ()


def get_docnames_for(code_list: str, doctype: str, code: str) -> tuple[str]:
	"""Return the record name for a given common code"""
	CommonCode = frappe.qb.DocType("Common Code")
	DynamicLink = frappe.qb.DocType("Dynamic Link")

	docnames = (
		frappe.qb.from_(CommonCode)
		.join(DynamicLink)
		.on((CommonCode.name == DynamicLink.parent) & (DynamicLink.parenttype == "Common Code"))
		.select(DynamicLink.link_name)
		.where(
			(DynamicLink.link_doctype == doctype)
			& (CommonCode.common_code == code)
			& (CommonCode.code_list == code_list)
		)
		.distinct()
		.orderby(DynamicLink.idx)
	).run()

	return tuple(d[0] for d in docnames) if docnames else ()


def get_default_code(code_list: str) -> str | None:
	"""Return the default common code for a given code list"""
	code_id = frappe.db.get_value("Code List", code_list, "default_common_code")
	return frappe.db.get_value("Common Code", code_id, "common_code") if code_id else None
