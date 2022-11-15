# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document

class ProjectWorkshop(Document):
	pass


@frappe.whitelist()
def get_project_workshop_details(project_workshop):
	doc = frappe.get_cached_doc("Project Workshop", project_workshop)
	out = frappe._dict()
	out.service_manager = doc.service_manager
	return out
