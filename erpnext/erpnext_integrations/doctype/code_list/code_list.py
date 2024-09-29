# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CodeList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		publisher: DF.Data | None
		title: DF.Data | None
		version: DF.Data | None
	# end: auto-generated types

	def get_code_for(self, doctype: str, name: str):
		"""Get code for a doctype and name"""
		CommonCode = frappe.qb.DocType("Common Code")
		DynamicLink = frappe.qb.DocType("Dynamic Link")

		code = (
			frappe.qb.from_(CommonCode)
			.join(DynamicLink)
			.on((CommonCode.name == DynamicLink.parent) & (DynamicLink.parenttype == "Common Code"))
			.select(CommonCode.name)
			.where(
				(DynamicLink.link_doctype == doctype)
				& (DynamicLink.link_name == name)
				& (CommonCode.code_list == self.name)
			)
		).run()

		return code[0][0] if code else None
