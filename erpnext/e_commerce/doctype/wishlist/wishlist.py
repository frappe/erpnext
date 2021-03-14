# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Wishlist(Document):
	pass

@frappe.whitelist()
def add_to_wishlist(item_code, price):
	"""Insert Item into wishlist."""
	web_item_data = frappe.db.get_value("Website Item", {"item_code": item_code},
		["image", "website_warehouse", "name", "item_name"], as_dict=1)

	wished_item_dict = {
		"item_code": item_code,
		"item_name": web_item_data.get("item_name"),
		"website_item": web_item_data.get("name"),
		"price": frappe.utils.flt(price),
		"image": web_item_data.get("image"),
		"website_warehouse": web_item_data.get("website_warehouse")
	}

	if not frappe.db.exists("Wishlist", frappe.session.user):
		# initialise wishlist
		wishlist = frappe.get_doc({"doctype": "Wishlist"})
		wishlist.user = frappe.session.user
		wishlist.append("items", wished_item_dict)
		wishlist.save(ignore_permissions=True)
	else:
		wishlist = frappe.get_doc("Wishlist", frappe.session.user)
		item = wishlist.append('items', wished_item_dict)
		item.db_insert()

	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.set_cookie("wish_count", str(len(wishlist.items)))

@frappe.whitelist()
def remove_from_wishlist(item_code):
	if frappe.db.exists("Wishlist Items", {"item_code": item_code}):
		frappe.db.sql("""
			delete
			from `tabWishlist Items`
			where item_code=%(item_code)s
		"""%{"item_code": frappe.db.escape(item_code)})

		frappe.db.commit()

		wishlist = frappe.get_doc("Wishlist", frappe.session.user)
		if hasattr(frappe.local, "cookie_manager"):
			frappe.local.cookie_manager.set_cookie("wish_count", str(len(wishlist.items)))