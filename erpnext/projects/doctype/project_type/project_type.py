# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint
from frappe.model.document import Document


class ProjectType(Document):
	pass


@frappe.whitelist()
def get_project_type_defaults(project_type):
	doc = frappe.get_cached_doc("Project Type", project_type)

	defaults_fields = [
		'is_warranty_claim', 'is_internal',
		'cash_billing', 'has_stin',
		'is_periodic_maintenance', 'is_general_repair',
	]

	out = frappe._dict()
	for f in defaults_fields:
		if doc.get(f):
			out[f] = cint(doc.get(f) == "Yes")

	return out
