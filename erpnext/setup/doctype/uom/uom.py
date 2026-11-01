# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document


def validate_uoms_are_enabled(uoms):
	uoms = list(set(filter(None, uoms)))
	if not uoms:
		return

	disabled_uoms = frappe.get_all("UOM", filters={"name": ["in", uoms], "enabled": 0}, pluck="name")
	if disabled_uoms:
		frappe.throw(_("Unit of Measure {0} is disabled.").format(frappe.bold(", ".join(disabled_uoms))))


class UOM(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Link | None
		common_code: DF.Data | None
		description: DF.SmallText | None
		enabled: DF.Check
		must_be_whole_number: DF.Check
		symbol: DF.Data | None
		uom_name: DF.Data
	# end: auto-generated types

	def before_rename(self, old_name, new_name, merge=False):
		if not merge:
			return

		item_uoms = {}
		for row in frappe.get_all(
			"UOM Conversion Detail",
			filters={"parenttype": "Item", "uom": ["in", [old_name, new_name]]},
			fields=["parent", "uom"],
		):
			item_uoms.setdefault(row.parent, set()).add(row.uom)

		if conflicting_items := [item for item, uoms in item_uoms.items() if len(uoms) == 2]:
			frappe.throw(
				_("Cannot merge Unit of Measure {0} into {1} because Item {2} uses both.").format(
					frappe.bold(old_name), frappe.bold(new_name), frappe.bold(conflicting_items[0])
				)
			)
