# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe


from frappe.utils import flt
from frappe import _

from frappe.utils.nestedset import NestedSet

class Territory(NestedSet):
	nsm_parent_field = 'parent_territory'

	def validate(self):
		for d in self.get('targets') or []:
			if not flt(d.target_qty) and not flt(d.target_alt_uom_qty) and not flt(d.target_amount):
				frappe.throw(_("Row {0}: Either Target Stock Qty or Target Contents Qty or Target Amount is mandatory.")
					.format(d.idx))

	def on_update(self):
		super(Territory, self).on_update()
		self.validate_one_root()

def on_doctype_update():
	frappe.db.add_index("Territory", ["lft", "rgt"])