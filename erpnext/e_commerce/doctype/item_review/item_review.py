# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.model.document import Document
from frappe.utils import cint, flt

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)


class UnverifiedReviewer(frappe.ValidationError):
	pass


class ItemReview(Document):
	def after_insert(self):
		# regenerate cache on review creation
		reviews_dict = get_queried_reviews(self.website_item)
		set_reviews_in_cache(self.website_item, reviews_dict)

	def after_delete(self):
		# regenerate cache on review deletion
		reviews_dict = get_queried_reviews(self.website_item)
		set_reviews_in_cache(self.website_item, reviews_dict)


@frappe.whitelist()
def get_item_reviews(web_item, start=0, end=10, data=None):
	"Get Website Item Review Data."
	start, end = cint(start), cint(end)
	settings = get_shopping_cart_settings()

	# Get cached reviews for first page (start=0)
	# avoid cache when page is different
	from_cache = not bool(start)

	if not data:
		data = frappe._dict()

	if settings and settings.get("enable_reviews"):
		reviews_cache = frappe.cache().hget("item_reviews", web_item)
		if from_cache and reviews_cache:
			data = reviews_cache
		else:
			data = get_queried_reviews(web_item, start, end, data)
			if from_cache:
				set_reviews_in_cache(web_item, data)

	return data


def get_queried_reviews(web_item, start=0, end=10, data=None):
	"""
	Query Website Item wise reviews and cache if needed.
	Cache stores only first page of reviews i.e. 10 reviews maximum.
	Returns:
	        dict: Containing reviews, average ratings, % of reviews per rating and total reviews.
	"""
	if not data:
		data = frappe._dict()

	data.reviews = frappe.db.get_all(
		"Item Review",
		filters={"website_item": web_item},
		fields=["*"],
		limit_start=start,
		limit_page_length=end,
	)

	rating_data = frappe.db.get_all(
		"Item Review",
		filters={"website_item": web_item},
		fields=["avg(rating) as average, count(*) as total"],
	)[0]

	data.average_rating = flt(rating_data.average, 1)
	data.average_whole_rating = flt(data.average_rating, 0)

	# get % of reviews per rating
	reviews_per_rating = []
	for i in range(1, 6):
		count = frappe.db.get_all(
			"Item Review", filters={"website_item": web_item, "rating": i}, fields=["count(*) as count"]
		)[0].count

		percent = flt((count / rating_data.total or 1) * 100, 0) if count else 0
		reviews_per_rating.append(percent)

	data.reviews_per_rating = reviews_per_rating
	data.total_reviews = rating_data.total

	return data


def set_reviews_in_cache(web_item, reviews_dict):
	frappe.cache().hset("item_reviews", web_item, reviews_dict)


@frappe.whitelist()
def add_item_review(web_item, title, rating, comment=None):
	"""Add an Item Review by a user if non-existent."""
	if frappe.session.user == "Guest":
		# guest user should not reach here ideally in the case they do via an API, throw error
		frappe.throw(_("You are not verified to write a review yet."), exc=UnverifiedReviewer)

	if not frappe.db.exists("Item Review", {"user": frappe.session.user, "website_item": web_item}):
		doc = frappe.get_doc(
			{
				"doctype": "Item Review",
				"user": frappe.session.user,
				"customer": get_customer(),
				"website_item": web_item,
				"item": frappe.db.get_value("Website Item", web_item, "item_code"),
				"review_title": title,
				"rating": rating,
				"comment": comment,
			}
		)
		doc.published_on = datetime.today().strftime("%d %B %Y")
		doc.insert()


def get_customer(silent=False):
	"""
	silent: Return customer if exists else return nothing. Dont throw error.
	"""
	user = frappe.session.user
	contact_name = get_contact_name(user)
	customer = None

	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)
		for link in contact.links:
			if link.link_doctype == "Customer":
				customer = link.link_name
				break

	if customer:
		return frappe.db.get_value("Customer", customer)
	elif silent:
		return None
	else:
		# should not reach here unless via an API
		frappe.throw(
			_("You are not a verified customer yet. Please contact us to proceed."), exc=UnverifiedReviewer
		)
