# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.nestedset import get_root_of

def execute():
	if not frappe.db.sql("select name from `tabPrice List` where buying=1"):
		create_price_list(_("Standard Buying"), buying=1)

	if not frappe.db.sql("select name from `tabPrice List` where selling=1"):
		create_price_list(_("Standard Selling"), selling=1)

def create_price_list(pl_name, buying=0, selling=0):
	price_list = frappe.get_doc({
		"doctype": "Price List",
		"price_list_name": pl_name,
		"enabled": 1,
		"buying": buying,
		"selling": selling,
		"currency": frappe.db.get_default("currency"),
		"valid_for_territories": [{
			"territory": get_root_of("Territory")
		}]
	})
	price_list.insert()
