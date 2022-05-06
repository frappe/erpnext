# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Wishlist(Document):
	pass


@frappe.whitelist()
def add_to_wishlist(item_code):
	"""Insert Item into wishlist."""

	if frappe.db.exists("Wishlist Item", {"item_code": item_code, "parent": frappe.session.user}):
		return

	web_item_data = frappe.db.get_value(
		"Website Item",
		{"item_code": item_code},
		["image", "website_warehouse", "name", "web_item_name", "item_name", "item_group", "route"],
		as_dict=1,
	)

	wished_item_dict = {
		"item_code": item_code,
		"item_name": web_item_data.get("item_name"),
		"item_group": web_item_data.get("item_group"),
		"website_item": web_item_data.get("name"),
		"web_item_name": web_item_data.get("web_item_name"),
		"image": web_item_data.get("image"),
		"warehouse": web_item_data.get("website_warehouse"),
		"route": web_item_data.get("route"),
	}

	if not frappe.db.exists("Wishlist", frappe.session.user):
		# initialise wishlist
		wishlist = frappe.get_doc({"doctype": "Wishlist"})
		wishlist.user = frappe.session.user
		wishlist.append("items", wished_item_dict)
		wishlist.save(ignore_permissions=True)
	else:
		wishlist = frappe.get_doc("Wishlist", frappe.session.user)
		item = wishlist.append("items", wished_item_dict)
		item.db_insert()

	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.set_cookie("wish_count", str(len(wishlist.items)))


@frappe.whitelist()
def remove_from_wishlist(item_code):
	if frappe.db.exists("Wishlist Item", {"item_code": item_code, "parent": frappe.session.user}):
		frappe.db.delete("Wishlist Item", {"item_code": item_code, "parent": frappe.session.user})
		frappe.db.commit()  # nosemgrep

		wishlist_items = frappe.db.get_values("Wishlist Item", filters={"parent": frappe.session.user})

		if hasattr(frappe.local, "cookie_manager"):
			frappe.local.cookie_manager.set_cookie("wish_count", str(len(wishlist_items)))
