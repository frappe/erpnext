# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import copy

import frappe
from frappe.model.document import Document


class Brand(Document):
	pass

def get_brand_defaults(item, company):
	item = frappe.get_cached_doc("Item", item)
	if item.brand:
		brand = frappe.get_cached_doc("Brand", item.brand)

		for d in brand.brand_defaults or []:
			if d.company == company:
				row = copy.deepcopy(d.as_dict())
				row.pop("name")
				return row

	return frappe._dict()
