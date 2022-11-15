# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint
from frappe.model.document import Document
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series


class ProjectsSettings(Document):
	def validate(self):
		for key in ["project_naming_by"]:
			frappe.db.set_default(key, self.get(key, ""))

		use_naming_series = self.get("project_naming_by") == "Naming Series"

		set_by_naming_series("Project", "project_name", use_naming_series, hide_name_field=False)
		make_property_setter("Project", "project_name", "reqd", cint(not use_naming_series), "Check")
		make_property_setter("Project", "project_number", "hidden", cint(not use_naming_series), "Check")
