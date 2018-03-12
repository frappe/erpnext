# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

doctype_series_map = {
	'Attendance': 'ATT-',
	'C-Form': 'C-FORM-',
	'Customer': 'CUST-',
	'Warranty Claim': 'CI-',
	'Delivery Note': 'DN-',
	'Installation Note': 'IN-',
	'Item': 'ITEM-',
	'Journal Entry': 'JV-',
	'Lead': 'LEAD-',
	'Opportunity': 'OPTY-',
	'Packing Slip': 'PS-',
	'Production Order': 'PRO-',
	'Purchase Invoice': 'PINV-',
	'Purchase Order': 'PO-',
	'Purchase Receipt': 'PREC-',
	'Quality Inspection': 'QI-',
	'Quotation': 'QTN-',
	'Sales Invoice': 'SINV-',
	'Sales Order': 'SO-',
	'Stock Entry': 'STE-',
	'Supplier': 'SUPP-',
	'Supplier Quotation': 'SQTN-',
	'Issue': 'SUP-'
}

def execute():
	series_to_set = get_series_to_set()
	for doctype, opts in series_to_set.items():
		set_series(doctype, opts["options"], opts["default"])

def set_series(doctype, options, default):
	make_property_setter(doctype, "naming_series", "options", options, "Text")
	make_property_setter(doctype, "naming_series", "default", default, "Text")

def get_series_to_set():
	series_to_set = {}

	for doctype, new_series in doctype_series_map.items():
		# you can't fix what does not exist :)
		if not frappe.db.a_row_exists(doctype):
			continue

		series_to_preserve = get_series_to_preserve(doctype, new_series)

		if not series_to_preserve:
			continue

		default_series = get_default_series(doctype, new_series)
		if not default_series:
			continue

		existing_series = (frappe.get_meta(doctype).get_field("naming_series").options or "").split("\n")
		existing_series = filter(None, [d.strip() for d in existing_series])

		if (not (set(existing_series).difference(series_to_preserve) or set(series_to_preserve).difference(existing_series))
			and len(series_to_preserve)==len(existing_series)):
			# print "No change for", doctype, ":", existing_series, "=", series_to_preserve
			continue

		# set naming series property setter
		series_to_preserve = list(set(series_to_preserve + existing_series))
		if new_series in series_to_preserve:
			series_to_preserve.remove(new_series)

		if series_to_preserve:
			series_to_set[doctype] = {"options": "\n".join(series_to_preserve), "default": default_series}

	return series_to_set

def get_series_to_preserve(doctype, new_series):
	series_to_preserve = frappe.db.sql_list("""select distinct naming_series from `tab{doctype}`
		where ifnull(naming_series, '') not in ('', %s)""".format(doctype=doctype), new_series)

	series_to_preserve.sort()

	return series_to_preserve

def get_default_series(doctype, new_series):
	default_series = frappe.db.sql("""select naming_series from `tab{doctype}` where ifnull(naming_series, '') not in ('', %s)
		and creation=(select max(creation) from `tab{doctype}`
			where ifnull(naming_series, '') not in ('', %s)) order by creation desc limit 1""".format(doctype=doctype),
		(new_series, new_series))

	if not (default_series and default_series[0][0]):
		print("[Skipping] Cannot guess which naming series to use for", doctype)
		return

	return default_series[0][0]
