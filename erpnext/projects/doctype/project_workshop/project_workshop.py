# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class ProjectWorkshop(Document):
	def get_default_cost_center(self, company):
		if not company:
			return None

		for d in self.default_cost_centers:
			if d.company == company:
				return d.cost_center


@frappe.whitelist()
def get_project_workshop_details(project_workshop, company):
	doc = frappe.get_cached_doc("Project Workshop", project_workshop)

	out = frappe._dict()
	out.service_manager = doc.service_manager
	out.cost_center = doc.get_default_cost_center(company)

	return out
