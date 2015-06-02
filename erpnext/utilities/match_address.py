# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import re

"""
# Selection based on Address

- The DocType should contain the following fields:
	- `if_address_matches` with possible values as ["Any Country", "Home Country", "Rest of the World", "Country, State, Post Code Pattern"]
	- `country`
	- `state`
	- `post_code_pattern`
"""

def validate_address_params(doc):
	validate_post_code_pattern(doc)
	validate_unique_combinations(doc)

def validate_post_code_pattern(doc):
	value = doc.post_code_pattern
	if value:
		value = value.strip().upper()

		# 1 - post code pattern should be composed of numbers, letters, spaces, hyphens, dots and Xs
		# (some post codes contain letters - eg. AD100)
		if not re.match(r"^[\w\.\- ]+$", value, flags=re.UNICODE):
			frappe.throw(_("Post Code Pattern can only contain Numbers, Letters, Spaces, Hyphens, Dots and Xs"))

		# 2 - post code should contain Xs only at the end
		if not value.startswith(value.replace("X", "")):
			frappe.throw(_("Post Code Pattern can contain the placeholder 'X' only at the end"))

	# set the stripped and uppercase value or None
	doc.post_code_pattern = value or None

def validate_unique_combinations(doc):
	if doc.if_address_matches != "Country, State, Post Code Pattern":
		return

	# 1 - unique country - post code pattern combination
	if doc.country and doc.post_code_pattern:
		match_country_post_code = frappe.db.get_value(doc.doctype, filters={
			"country": doc.country,
			"post_code_pattern": doc.post_code_pattern,
			"name": ("!=", doc.name)
		})
		if match_country_post_code:
			frappe.throw(_("Another {0} exists for the combination of {1} and {2}")\
				.format(doc.doctype, doc.country, doc.post_code_pattern), frappe.DuplicateEntryError)

	# 2 - unique country - state combination
	elif doc.country and doc.state:
		match_country_state = frappe.db.get_value(doc.doctype, filters={
			"country": doc.country,
			"state": doc.state,
			"name": ("!=", doc.name)
		})
		if match_country_state:
			frappe.throw(_("Another {0} exists for the combination of {1} and {2}")\
				.format(doc.doctype, doc.country, doc.state), frappe.DuplicateEntryError)

	# 3 - unique country
	else:
		match_country = frappe.db.get_value(doc.doctype, filters={
			"country": doc.country,
			"state": ("in", ("", None)),
			"post_code_pattern": ("in", ("", None)),
			"name": ("!=", doc.name)
		})
		if match_country:
			frappe.throw(_("Another {0} exists for {1}").format(doc.doctype, doc.country), frappe.DuplicateEntryError)

def get_doc_from_address(doctype, address):
	"""
		Match address values with configuration to find the document.
		Search Order:
			1. If Address Matches == "Country, State, Post Code Pattern"
				a. (Country, Post Code)
				b. (Country, State)
				c. Country
			4. Is Home Country? (Country == Company's Country)
			5. Rest of the World (Country != Company's Country)
			6. Any Country
	"""
	name = (match_country_state_post_code_pattern(doctype, address)
		or match_home_or_rest_of_the_world(doctype, address)
		or match_any_country(doctype, address))

	if name:
		return frappe.get_doc(doctype, name)

def match_country_state_post_code_pattern(doctype, address):
	doc = None

	results = frappe.get_all(doctype,
		fields=["name", "country", "state", "post_code_pattern"],
		filters=prepare_filters(doctype, {
			"if_address_matches": "Country, State, Post Code Pattern",
			"country": address.country,
		}),
		order_by="creation asc") # to get consistent results everytime

	if results:
		doc = (_match_country_post_code_pattern(results, address)
			or _match_country_state(results, address)
			or _match_only_country(results, address))

	return doc

def _match_country_post_code_pattern(results, address):
	pass

def _match_country_state(results, address):
	pass

def _match_only_country(results, address):
	pass

def match_home_or_rest_of_the_world(doctype, address):
	pass

def match_any_country(doctype, address):
	results = frappe.get_all(doctype, filters=prepare_filters({
		"if_address_matches": "Any Country"
	}))
	return results[0].name if results else None

def prepare_filters(doctype, filters):
	meta = frappe.get_meta(doctype)
	if meta.get_field("enabled"):
		filters["enabled"] = 1
	elif meta.get_field("disabled"):
		filters["disabled"] = 0

	return filters
