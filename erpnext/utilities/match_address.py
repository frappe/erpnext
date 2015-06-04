# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import strip
import re

"""
# Selection based on Address

- The DocType should contain the following fields:
	- `if_address_matches` with possible values as ["Any Country", "Home Country", "Rest of the World", "Country, State, Postal Code Pattern"]
	- `country`
	- `state`
	- `postal_code_pattern`
"""

def validate_address_params(doc, unique=True):
	validate_postal_code_pattern(doc)

	if unique:
		validate_unique_combinations(doc)

def validate_postal_code_pattern(doc):
	value = doc.postal_code_pattern
	if value:
		value = value.strip().upper()

		# 1 - postal code pattern should be composed of numbers, letters, spaces, hyphens, dots and Xs
		# (some postal codes contain letters - eg. AD100)
		if not re.match(r"^[\w\.\- ]+$", value, flags=re.UNICODE):
			frappe.throw(_("Postal Code Pattern can only contain Numbers, Letters, Spaces, Hyphens, Dots and Xs"))

		# 2 - postal code should contain Xs only at the end
		if not value.startswith(value.replace("X", "")):
			frappe.throw(_("Postal Code Pattern can contain the placeholder 'X' only at the end"))

	# set the stripped and uppercase value or None
	doc.postal_code_pattern = value or None

def validate_unique_combinations(doc):
	if doc.if_address_matches == "Country, State, Postal Code Pattern":
		doc.postal_code_pattern = doc.postal_code_pattern and strip(doc.postal_code_pattern) or None

		# 1 - unique country - postal code pattern combination
		if doc.country and doc.postal_code_pattern:
			match_country_postal_code = frappe.get_all(doc.doctype,
				filters=prepare_filters(doc.doctype, doc.get("company"), {
					"country": doc.country,
					"postal_code_pattern": doc.postal_code_pattern,
					"name": ("!=", doc.name)
				}))
			if match_country_postal_code:
				frappe.throw(_("Another {0} exists for the combination of {1} and {2}")\
					.format(doc.doctype, doc.country, doc.postal_code_pattern), frappe.DuplicateEntryError)

		# 2 - unique country - state combination
		elif doc.country and doc.state:
			match_country_state = frappe.get_all(doc.doctype,
				filters=prepare_filters(doc.doctype, doc.get("company"), {
					"country": doc.country,
					"state": doc.state,
					"name": ("!=", doc.name)
				}))
			if match_country_state:
				frappe.throw(_("Another {0} exists for the combination of {1} and {2}")\
					.format(doc.doctype, doc.country, doc.state), frappe.DuplicateEntryError)

		# 3 - unique country
		else:
			match_country = frappe.get_all(doc.doctype,
				filters=prepare_filters(doc.doctype, doc.get("company"), {
					"country": doc.country,
					"state": ("in", ("", None)),
					"postal_code_pattern": ("in", ("", None)),
					"name": ("!=", doc.name)
				}))
			if match_country:
				frappe.throw(_("Another {0} exists for {1}").format(doc.doctype, doc.country), frappe.DuplicateEntryError)

	else:
		if frappe.get_all(doc.doctype,
			filters=prepare_filters(doc.doctype, doc.get("company"), {
				"if_address_matches": doc.if_address_matches,
				"name": ("!=", doc.name)
			})):
			frappe.throw(_("Another {0} exists for Address Matching with {1}").format(doc.doctype, doc.if_address_matches), frappe.DuplicateEntryError)


def get_all_from_address(doctype, company, address):
	"""
		Match address values with configuration to find the records.
		Returns a list of names
		Search Order:
			1. If Address Matches == "Country, State, Postal Code Pattern"
				a. (Country, Postal Code)
				b. (Country, State)
				c. Country
			4. Is Home Country? (Country == Company's Country)
			5. Rest of the World (Country != Company's Country)
			6. Any Country
	"""
	return (match_country_state_postal_code_pattern(doctype, company, address)
		or match_rest_of_the_cases(doctype, company, address))

def match_country_state_postal_code_pattern(doctype, company, address):
	if not address.country:
		return

	names = None

	# first filter by country
	results = frappe.get_all(doctype,
		fields=["name", "country", "state", "postal_code_pattern"],
		filters=prepare_filters(doctype, company, {
			"if_address_matches": "Country, State, Postal Code Pattern",
			"country": address.country,
		}),
		order_by="creation asc") # to get consistent results everytime

	if results:
		names = (_match_postal_code_pattern(results, address)
			or _match_state(results, address)
			or _match_only_country(results, address))

	return names

def _match_postal_code_pattern(results, address):
	address.pincode = address.pincode and strip(address.pincode) or None
	if not address.pincode:
		return

	names = []
	for d in results:
		if d.postal_code_pattern:
			# example: see if 400086 matches the pattern 4000XX
			if re.match(r"^{0}$".format(d.postal_code_pattern.replace("X", "\d")), address.pincode, flags=re.UNICODE):
				names.append(d.name)

	return names

def _match_state(results, address):
	address.state = address.state and strip(address.state) or None
	if not address.state:
		return

	return [d.name for d in results if (d.state and d.state==address.state)]

def _match_only_country(results, address):
	return [d.name for d in results if not (d.postal_code_pattern or d.state)]

def match_rest_of_the_cases(doctype, company, address):
	if not address.country:
		return

	def _get(match_type):
		results = frappe.get_all(doctype,
			fields=["name"],
			filters=prepare_filters(doctype, company, {
				"if_address_matches": match_type
			}),
			order_by="creation asc") # to get consistent results everytime

		return [d.name for d in results]

	home_country = frappe.db.get_value("Company", company, "country")

	return ((address.country==home_country and _get("Home Country"))
		or (address.country!=home_country and _get("Rest of the World"))
		or _get("Any Country"))

def prepare_filters(doctype, company, filters):
	meta = frappe.get_meta(doctype)
	if meta.get_field("enabled"):
		filters["enabled"] = 1
	elif meta.get_field("disabled"):
		filters["disabled"] = 0

	if meta.get_field("company"):
		filters["company"] = company

	return filters
