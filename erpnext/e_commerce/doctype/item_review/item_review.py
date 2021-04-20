# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe.model.document import Document
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.utils import flt, cint
from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import get_shopping_cart_settings

class ItemReview(Document):
	pass

@frappe.whitelist()
def get_item_reviews(web_item, start, end, data=None):
	if not data:
		data = frappe._dict()

	settings = get_shopping_cart_settings()

	if settings and settings.get("enable_reviews"):
		data.reviews = frappe.db.get_all("Item Review", filters={"website_item": web_item},
			fields=["*"], limit_start=cint(start), limit_page_length=cint(end))

		rating_data = frappe.db.get_all("Item Review", filters={"website_item": web_item},
			fields=["avg(rating) as average, count(*) as total"])[0]
		data.average_rating = flt(rating_data.average, 1)
		data.average_whole_rating = flt(data.average_rating, 0)

		# get % of reviews per rating
		reviews_per_rating = []
		for i in range(1,6):
			count = frappe.db.get_all("Item Review", filters={"website_item": web_item, "rating": i},
				fields=["count(*) as count"])[0].count

			percent = flt((count / rating_data.total or 1) * 100, 0) if count else 0
			reviews_per_rating.append(percent)

		data.reviews_per_rating = reviews_per_rating
		data.total_reviews = rating_data.total

		return data

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
		frappe.throw(_("You are not verified to write a review yet. Please contact us for verification."))