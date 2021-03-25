# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe.model.document import Document

from frappe.contacts.doctype.contact.contact import get_contact_name

class ItemReview(Document):
	pass

@frappe.whitelist()
def add_item_review(web_item, title, rating, comment=None):
	""" Add an Item Review by a user if non-existent. """
	if not frappe.db.exists("Item Review", {"user": frappe.session.user, "website_item": web_item}):
		doc = frappe.get_doc({
			"doctype": "Item Review",
			"user": frappe.session.user,
			"customer": get_customer(),
			"website_item": web_item,
			"item": frappe.db.get_value("Website Item", web_item, "item_code"),
			"review_title": title,
			"rating": rating,
			"comment": comment
		})
		doc.published_on = datetime.today().strftime("%d %B %Y")
		doc.insert()

def get_customer():
	user = frappe.session.user
	contact_name = get_contact_name(user)
	customer = None

	if contact_name:
		contact = frappe.get_doc('Contact', contact_name)
		for link in contact.links:
			if link.link_doctype == "Customer":
				customer = link.link_name
				break

	if customer:
		return frappe.db.get_value("Customer", customer)
	else:
		frappe.throw("You are not verified to write a review yet. Please contact us for verification.")