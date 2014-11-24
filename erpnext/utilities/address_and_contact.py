# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def load_address_and_contact(doc, key):
	"""Loads address list and contact list in `__onload`"""
	from erpnext.utilities.doctype.address.address import get_address_display

	doc.get("__onload").addr_list = [a.update({"display": get_address_display(a)}) \
		for a in frappe.get_all("Address",
			fields="*", filters={key: doc.name},
			order_by="is_primary_address desc, modified desc")]

	if doc.doctype != "Lead":
		doc.get("__onload").contact_list = frappe.get_all("Contact",
			fields="*", filters={key: doc.name},
			order_by="is_primary_contact desc, modified desc")
