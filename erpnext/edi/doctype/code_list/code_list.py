# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from lxml import etree

from erpnext.edi.doctype.common_code.common_code import CommonCode


class CodeList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		canonical_uri: DF.Data | None
		description: DF.SmallText | None
		publisher: DF.Data | None
		title: DF.Data | None
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

	def import_genericode(self, file_path, code_column, title_column=None, filters=None):
		"""Import genericode file and create Common Code entries"""
		parser = etree.XMLParser(remove_blank_text=True)
		tree = etree.parse(file_path, parser=parser)
		root = tree.getroot()

		# Extract Code List details
		self.title = root.find(".//Identification/ShortName").text
		self.version = root.find(".//Identification/Version").text
		self.canonical_uri = root.find(".//CanonicalUri").text
		# optionals
		self.description = getattr(root.find(".//Identification/LongName"), "text", None)
		self.publisher = getattr(root.find(".//Identification/Agency/ShortName"), "text", None)

		self.save()

		common_codes = CommonCode.import_genericode(file_path, self.name, code_column, title_column, filters)

		# Bulk insert common codes
		if common_codes:
			frappe.db.bulk_insert(
				"Common Code",
				fields=["name", "code_list", "common_code", "title", "additional_data"],
				values=[
					(cc["name"], cc["code_list"], cc["common_code"], cc["title"], cc["additional_data"])
					for cc in common_codes
				],
			)

		return {"code_list": self, "common_codes_count": len(common_codes)}
