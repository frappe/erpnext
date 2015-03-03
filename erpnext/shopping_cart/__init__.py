# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_fullname, flt
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import check_shopping_cart_enabled, get_default_territory

# TODO
# validate stock of each item in Website Warehouse or have a list of possible warehouses in Shopping Cart Settings
# Below functions are used for test cases

def get_quotation(user=None):
	if not user:
		user = frappe.session.user
	if user == "Guest":
		raise frappe.PermissionError

	check_shopping_cart_enabled()
	party = get_party(user)
	values = {
		"order_type": "Shopping Cart",
		party.doctype.lower(): party.name,
		"docstatus": 0,
		"contact_email": user,
		"selling_price_list": "_Test Price List Rest of the World"
	}

	try:
		quotation = frappe.get_doc("Quotation", values)
	except frappe.DoesNotExistError:
		quotation = frappe.new_doc("Quotation")
		quotation.update(values)
		if party.doctype == "Customer":
			quotation.contact_person = frappe.db.get_value("Contact", {"customer": party.name, "email_id": user})
		quotation.insert(ignore_permissions=True)

	return quotation

def set_item_in_cart(item_code, qty, user=None):
	validate_item(item_code)
	quotation = get_quotation(user=user)
	qty = flt(qty)
	quotation_item = quotation.get("items", {"item_code": item_code})

	if qty==0:
		if quotation_item:
			# remove
			quotation.get("items").remove(quotation_item[0])
	else:
		# add or update
		if quotation_item:
			quotation_item[0].qty = qty
		else:
			quotation.append("items", {
				"doctype": "Quotation Item",
				"item_code": item_code,
				"qty": qty
			})

	quotation.save(ignore_permissions=True)
	return quotation

def validate_item(item_code):
	item = frappe.db.get_value("Item", item_code, ["item_name", "show_in_website"], as_dict=True)
	if not item.show_in_website:
		frappe.throw(_("{0} cannot be purchased using Shopping Cart").format(item.item_name))

def get_party(user):
	def _get_party(user):
		customer = frappe.db.get_value("Contact", {"email_id": user}, "customer")
		if customer:
			return frappe.get_doc("Customer", customer)

		lead = frappe.db.get_value("Lead", {"email_id": user})
		if lead:
			return frappe.get_doc("Lead", lead)

		# create a lead
		lead = frappe.new_doc("Lead")
		lead.update({
			"email_id": user,
			"lead_name": get_fullname(user),
			"territory": guess_territory()
		})
		lead.insert(ignore_permissions=True)

		return lead

	if not getattr(frappe.local, "shopping_cart_party", None):
		frappe.local.shopping_cart_party = {}

	if not frappe.local.shopping_cart_party.get(user):
		frappe.local.shopping_cart_party[user] = _get_party(user)

	return frappe.local.shopping_cart_party[user]

def guess_territory():
	territory = None
	if frappe.session.get("session_country"):
		territory = frappe.db.get_value("Territory", frappe.session.get("session_country"))
	return territory or get_default_territory()
