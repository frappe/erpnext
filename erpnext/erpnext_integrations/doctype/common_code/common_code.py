# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
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

	pass


def on_doctype_update():
	frappe.db.add_unique(
		"Common Code", ["code_list", "common_code"], constraint_name="unique_code_list_common_code"
	)
