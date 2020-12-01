# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import copy

from frappe.model.document import Document


class ItemSource(Document):
	pass


def get_item_source_defaults(item, company):
	item = frappe.get_cached_doc("Item", item)

	if item.item_source:
		item_source = frappe.get_cached_doc("Item Source", item.item_source)

		for d in item_source.item_source_defaults or []:
			if d.company == company:
				row = copy.deepcopy(d.as_dict())
				row.pop("name")
				return row

	return frappe._dict()
