# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CommonCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.dynamic_link.dynamic_link import DynamicLink
		from frappe.types import DF

		applies_to: DF.Table[DynamicLink]
		code_list: DF.Link
		common_code: DF.Data
		description: DF.SmallText | None
		title: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if frappe.db.exists(
			"Common Code",
			{"code_list": self.code_list, "common_code": self.common_code, "name": ("!=", self.name)},
		):
			frappe.throw(
				_("Common Code {0} already exists in Code List {1}").format(self.common_code, self.code_list)
			)


def on_doctype_update():
	frappe.db.add_unique(
		"Common Code", ["code_list", "common_code"], constraint_name="unique_code_list_common_code"
	)
