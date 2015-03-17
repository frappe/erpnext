# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json

import frappe
from erpnext.shopping_cart.cart import get_lead_or_customer, update_cart_address
from frappe.desk.form.meta import get_meta

no_cache = 1
no_sitemap = 1

def get_context(context):
	def _get_fields(fieldnames):
		return [frappe._dict(zip(["label", "fieldname", "fieldtype", "options"],
				[df.label, df.fieldname, df.fieldtype, df.options]))
			for df in get_meta("Address").get("fields", {"fieldname": ["in", fieldnames]})]

	docname = doc = None
	title = "New Address"
	if frappe.form_dict.name:
		doc = frappe.get_doc("Address", frappe.form_dict.name)
		docname = doc.name
		title = doc.name

	return {
		"doc": doc,
		"meta": frappe._dict({
			"left_fields": _get_fields(["address_title", "address_type", "address_line1", "address_line2",
				"city", "state", "pincode", "country"]),
			"right_fields": _get_fields(["email_id", "phone", "fax", "is_primary_address",
				"is_shipping_address"])
		}),
		"docname": docname,
		"title": title
	}

@frappe.whitelist()
def save_address(fields, address_fieldname=None):
	party = get_lead_or_customer()
	fields = json.loads(fields)

	if fields.get("name"):
		doc = frappe.get_doc("Address", fields.get("name"))
	else:
		doc = frappe.get_doc({"doctype": "Address", "__islocal": 1})

	doc.update(fields)

	party_fieldname = party.doctype.lower()
	doc.update({
		party_fieldname: party.name,
		(party_fieldname + "_name"): party.get(party_fieldname + "_name")
	})
	doc.flags.ignore_permissions = True
	doc.save()

	if address_fieldname:
		update_cart_address(address_fieldname, doc.name)

	return doc.name
