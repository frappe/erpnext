# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
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
			if d.applicable_item_code in visited:
				frappe.throw(_("Row #{0}: Duplicate Applicable Item {1}")
					.format(d.idx, frappe.bold(d.applicable_item_code)))

			visited.add(d.applicable_item_code)

	def validate_duplicate_applicable_item_groups(self):
		visited = set()
		for d in self.applicable_item_groups:
			if d.applicable_item_group in visited:
				frappe.throw(_("Row #{0}: Duplicate Applicable Item Group {1}")
					.format(d.idx, frappe.bold(d.applicable_item_group)))

			visited.add(d.applicable_item_group)


@frappe.whitelist()
def add_project_template_items(target_doc, project_template, applies_to_item=None, item_group=None, items_type=None,
		check_duplicate=True, project_template_detail=None, postprocess=True):
	from erpnext.stock.doctype.item_applicable_item.item_applicable_item import add_applicable_items,\
		append_applicable_items

	if isinstance(target_doc, string_types):
		target_doc = frappe.get_doc(json.loads(target_doc))

	if not project_template_detail and project_template:
		project_template_detail = frappe._dict({'project_template': project_template})

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

		if applicable_items_groups:
			target_doc = add_applicable_items(target_doc, applies_to_item, item_groups=applicable_items_groups,
				items_type=items_type, check_duplicate=check_duplicate, project_template_detail=project_template_detail,
				postprocess=False)

	# get applicable items from project template
	project_template_items = get_project_template_items(project_template, item_group=item_group, items_type=items_type)

	append_applicable_items(target_doc, project_template_items, check_duplicate=check_duplicate,
		project_template_detail=project_template_detail)

	# postprocess
	if postprocess:
		target_doc.run_method("set_missing_values")
		target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


def get_project_template_items(project_template, item_group=None, items_type=None):
	from erpnext.stock.doctype.item_applicable_item.item_applicable_item import filter_applicable_item

	project_template_doc = frappe.get_cached_doc("Project Template", project_template)

	item_groups = []
	if item_group:
		item_groups.append(item_group)

	project_template_items = []

	for pt_item in project_template_doc.applicable_items:
		if filter_applicable_item(pt_item, item_groups, items_type=items_type):
			continue

		project_template_items.append(pt_item)

	return project_template_items


@frappe.whitelist()
def guess_project_template(project_template_category, applies_to_item):
	project_template = frappe.db.get_value("Project Template", {
		'project_template_category': project_template_category,
		'applies_to_item': applies_to_item
	})

	if not project_template:
		applies_to_variant_of = frappe.get_cached_value("Item", applies_to_item, "variant_of")
		if applies_to_variant_of:
			project_template = frappe.db.get_value("Project Template", {
				'project_template_category': project_template_category,
				'applies_to_item': applies_to_variant_of
			})

	return project_template
