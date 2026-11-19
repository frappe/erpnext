# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet

from erpnext.setup.doctype.target_detail.target_detail import validate_targets
from erpnext.setup.utils import set_root_as_default_parent


class Territory(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.target_detail.target_detail import TargetDetail

		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_territory: DF.Link | None
		rgt: DF.Int
		targets: DF.Table[TargetDetail]
		territory_manager: DF.Link | None
		territory_name: DF.Data
	# end: auto-generated types

	nsm_parent_field = "parent_territory"

	def validate(self):
		validate_targets(self.get("targets"))
		set_root_as_default_parent(self)

		for d in self.get("targets") or []:
			if not flt(d.target_qty) and not flt(d.target_amount):
				frappe.throw(_("Either target qty or target amount is mandatory"))

	def on_update(self):
		super().on_update()
		self.validate_one_root()


def on_doctype_update():
	frappe.db.add_index("Territory", ["lft", "rgt"])


def restrict_customer_territory_permissions():
	"""Clear output and sharing grants without Read after custom permissions are synced."""
	ptypes = ("print", "email", "export", "report", "share")
	for row in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Territory", "role": "Customer", "permlevel": 0, "read": 0},
		fields=["name", *ptypes],
	):
		values = {ptype: 0 for ptype in ptypes if row.get(ptype)}
		if values:
			rule = frappe.get_doc("Custom DocPerm", row.name)
			rule.update(values)
			rule.save()
