# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import strip_html, cstr
from frappe.model.document import Document
from six import string_types
import json


class ItemApplicableItem(Document):
	pass


@frappe.whitelist()
def add_applicable_items(target_doc, applies_to_item, item_groups=None, items_type=None, check_duplicate=True,
		project_template_detail=None, postprocess=True):
	if isinstance(target_doc, string_types):
		target_doc = frappe.get_doc(json.loads(target_doc))
	if isinstance(item_groups, string_types):
		item_groups = json.loads(item_groups)

	if not item_groups:
		item_groups = []

	if not target_doc.meta.has_field('items'):
		frappe.throw(_("Target document does not have items table"))

	# remove first empty row
	if target_doc.get('items') and not target_doc.items[0].item_code and not target_doc.items[0].item_name:
		target_doc.remove(target_doc.items[0])

	applicable_items = get_applicable_items(applies_to_item, item_groups, items_type=items_type)

	append_applicable_items(target_doc, applicable_items, check_duplicate=check_duplicate,
		project_template_detail=project_template_detail)

	# postprocess
	if postprocess:
		target_doc.run_method("set_missing_values")
		target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


def get_applicable_items(applies_to_item, item_groups, items_type=None):
	applicable_items = []
	item_groups_in_variant = set()

	applies_to_item_doc = frappe.get_cached_doc("Item", applies_to_item)
	for applicable_item in applies_to_item_doc.applicable_items:
		if applicable_item.applicable_item_code:
			if filter_applicable_item(applicable_item, item_groups, items_type=items_type):
				continue

			applicable_item_group = frappe.get_cached_value("Item", applicable_item.applicable_item_code, "item_group")
			item_groups_in_variant.add(applicable_item_group)
			applicable_items.append(applicable_item)

	if applies_to_item_doc.variant_of:
		applies_to_item_template_doc = frappe.get_cached_doc("Item", applies_to_item_doc.variant_of)
		for applicable_item in applies_to_item_template_doc.applicable_items:
			if applicable_item.applicable_item_code:
				if filter_applicable_item(applicable_item, item_groups, items_type=items_type):
					continue

				# do not get applicable item from template if item group in variant exist/is overridden
				applicable_item_group = frappe.get_cached_value("Item", applicable_item.applicable_item_code, "item_group")
				if applicable_item_group in item_groups_in_variant:
					continue

				applicable_items.append(applicable_item)

	return applicable_items


def append_applicable_items(target_doc, applicable_items, check_duplicate=True, project_template_detail=None):
	if isinstance(project_template_detail, string_types):
		project_template_detail = frappe._dict(json.loads(project_template_detail))

	existing_item_codes = [d.item_code for d in target_doc.items if d.item_code]

	for applicable_item in applicable_items:
		if applicable_item.applicable_item_code:
			# do not duplicate item
			if check_duplicate and applicable_item.applicable_item_code in existing_item_codes:
				continue

			# add item
			trn_item = target_doc.append('items')
			trn_item.item_code = applicable_item.applicable_item_code
			trn_item.qty = applicable_item.applicable_qty
			trn_item.uom = applicable_item.applicable_uom

			if project_template_detail:
				if trn_item.meta.has_field('project_template'):
					trn_item.project_template = project_template_detail.get('project_template')
				if trn_item.meta.has_field('project_template_detail'):
					trn_item.project_template_detail = project_template_detail.get('name')

				if applicable_item.get('use_template_name') and project_template_detail.get('project_template_name'):
					trn_item.item_name = project_template_detail.get('project_template_name')

				if applicable_item.get('use_template_description') and strip_html(cstr(project_template_detail.get('description'))).strip():
					trn_item.description = project_template_detail.description


def filter_applicable_item(applicable_item, item_groups, items_type=None):
	# filter out inactive applicable item
	if applicable_item.get('inactive'):
		return True

	applicable_item_doc = frappe.get_cached_doc("Item", applicable_item.applicable_item_code)

	# filter by item group
	if item_groups and applicable_item_doc.item_group not in item_groups:
		return True

	# filter by stock item / service item
	if items_type == "stock" and not applicable_item_doc.is_stock_item:
		return True
	elif items_type == "service" and (applicable_item_doc.is_stock_item or applicable_item_doc.is_fixed_asset):
		return True

	return False
