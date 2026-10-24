# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class TargetDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		distribution_id: DF.Link
		fiscal_year: DF.Link
		item_group: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		target_amount: DF.Float
		target_qty: DF.Float
	# end: auto-generated types

	pass


def validate_duplicate_targets(targets):
	seen = set()
	for target in targets or []:
		key = (target.fiscal_year, target.item_group or None)
		if key in seen:
			frappe.throw(
				_("Row {0}: A target already exists for this fiscal year and item group.").format(target.idx)
			)
		seen.add(key)
