# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate, cint
from frappe.utils.nestedset import get_root_of
from frappe.frappeclient import FrappeClient
from frappe.contacts.doctype.contact.contact import get_default_contact

@frappe.whitelist()
def enable_hub():
	hub_settings = frappe.get_doc('Hub Settings')
	hub_settings.register()
	frappe.db.commit()
	return hub_settings
