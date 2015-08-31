# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from erpnext.shopping_cart.cart import get_lead_or_customer

no_cache = 1
no_sitemap = 1

def get_context(context):
	party = get_lead_or_customer()
	if party.doctype == "Lead":
		mobile_no = party.mobile_no
		phone = party.phone
	else:
		mobile_no, phone = frappe.db.get_value("Contact", {"email_id": frappe.session.user, 
			"customer": party.name}, ["mobile_no", "phone"])
		
	return {
		"company_name": cstr(party.customer_name if party.doctype == "Customer" else party.company_name),
		"mobile_no": cstr(mobile_no),
		"phone": cstr(phone)
	}
	
@frappe.whitelist()
def update_user(fullname, password=None, company_name=None, mobile_no=None, phone=None):
	from erpnext.shopping_cart.cart import update_party
	update_party(fullname, company_name, mobile_no, phone)
	
	if not fullname:
		return _("Name is required")
		
	frappe.db.set_value("User", frappe.session.user, "first_name", fullname)
	frappe.local.cookie_manager.set_cookie("full_name", fullname)
	
	return _("Updated")
	