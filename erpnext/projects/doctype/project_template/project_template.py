# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
from six import string_types
import json


class ProjectTemplate(Document):
	def validate(self):
		self.validate_duplicate_items()
		self.validate_duplicate_applicable_item_groups()

	def validate_duplicate_items(self):
		visited = set()
		for d in self.applicable_items:
			key = (cstr(d.applicable_item_code), cstr(d.applies_to_item))
			if key in visited:
				frappe.throw(_("Row #{0}: Duplicate Applicable Item {1}")
					.format(d.idx, frappe.bold(d.applicable_item_code)))

			visited.add(key)

	def validate_duplicate_applicable_item_groups(self):
		visited = set()
		for d in self.applicable_item_groups:
			if d.applicable_item_group in visited:
				frappe.throw(_("Row #{0}: Duplicate Applicable Item Group {1}")
					.format(d.idx, frappe.bold(d.applicable_item_group)))

			visited.add(d.applicable_item_group)


@frappe.whitelist()
def add_project_template_items(target_doc, project_template, applies_to_item=None, item_group=None,
		get_stock_items=True, get_service_items=True, project_template_detail=None, postprocess=True):
	from erpnext.stock.doctype.item_applicable_item.item_applicable_item import add_applicable_items,\
		append_applicable_items

	if isinstance(target_doc, string_types):
		target_doc = frappe.get_doc(json.loads(target_doc))

	if not target_doc.meta.has_field('items'):
		frappe.throw(_("Target document does not have items table"))

	# remove first empty row
	if target_doc.get('items') and not target_doc.items[0].item_code and not target_doc.items[0].item_name:
		target_doc.remove(target_doc.items[0])

	project_template_doc = frappe.get_cached_doc("Project Template", project_template)

	# get applicable items from item master
	if applies_to_item:
		applicable_items_groups = [d.applicable_item_group for d in project_template_doc.applicable_item_groups
			if d.applicable_item_group and (not item_group or d.applicable_item_group == item_group)]

		target_doc = add_applicable_items(target_doc, applies_to_item, item_groups=applicable_items_groups,
			get_stock_items=get_stock_items, get_service_items=get_service_items,
			project_template_detail=project_template_detail, postprocess=False)

	# get applicable items from project template
	project_template_items = get_project_template_items(project_template, applies_to_item, item_group=item_group,
		get_stock_items=get_stock_items, get_service_items=get_service_items)

	append_applicable_items(target_doc, project_template_items, project_template_detail=project_template_detail)

	# postprocess
	if postprocess:
		target_doc.run_method("set_missing_values")
		target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


def get_project_template_items(project_template, applies_to_item=None, item_group=None, get_stock_items=True,
		get_service_items=True):
	from erpnext.stock.doctype.item_applicable_item.item_applicable_item import filter_applicable_item

	project_template_doc = frappe.get_cached_doc("Project Template", project_template)

	item_groups = []
	if item_group:
		item_groups.append(item_group)

	project_template_items = []

	for pt_item in project_template_doc.applicable_items:
		# check applicability
		if pt_item.applies_to_item:
			# project template item is applicable to some item but no item provided
			if not applies_to_item:
				continue

			# if item does not match applies to nor template of applies to
			applies_to_item_template = frappe.get_cached_value("Item", applies_to_item, "variant_of")
			if pt_item.applies_to_item not in (applies_to_item, applies_to_item_template):
				continue

		# filter by item group
		if filter_applicable_item(pt_item, item_groups, get_stock_items=get_stock_items,
				get_service_items=get_service_items):
			continue

		project_template_items.append(pt_item)

	return project_template_items
