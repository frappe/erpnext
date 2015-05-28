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

