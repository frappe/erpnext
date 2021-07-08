# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint

from erpnext.e_commerce.product_query import ProductQuery
from erpnext.e_commerce.filters import ProductFiltersBuilder
from erpnext.setup.doctype.item_group.item_group import get_child_groups

@frappe.whitelist(allow_guest=True)
def get_product_filter_data():
	"""Get pre-rendered filtered products and discount filters on load."""
	if frappe.form_dict:
		search = frappe.form_dict.search
		field_filters = frappe.parse_json(frappe.form_dict.field_filters)
		attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)
		start = cint(frappe.parse_json(frappe.form_dict.start)) if frappe.form_dict.start else 0
		item_group = frappe.form_dict.item_group
	else:
		search, attribute_filters, item_group = None, None, None
		field_filters = {}
		start = 0

	sub_categories = []
	if item_group:
		field_filters['item_group'] = item_group
		sub_categories = get_child_groups(item_group)

	engine = ProductQuery()
	result = engine.query(attribute_filters, field_filters, search_term=search,
		start=start, item_group=item_group)

	# discount filter data
	filters = {}
	discounts = result["discounts"]

	if discounts:
		filter_engine = ProductFiltersBuilder()
		filters["discount_filters"] = filter_engine.get_discount_filters(discounts)

	return {
		"items": result["items"] or [],
		"filters": filters,
		"settings": engine.settings,
		"sub_categories": sub_categories,
		"items_count": result["items_count"]
	}

@frappe.whitelist(allow_guest=True)
def get_guest_redirect_on_action():
	return frappe.db.get_single_value("E Commerce Settings", "redirect_on_action")