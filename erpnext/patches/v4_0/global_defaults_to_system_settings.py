# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	global_defauls = frappe.db.get_value("Global Defaults", None,
		["time_zone", "date_format", "number_format", "float_precision", "session_expiry"])

	if global_defauls:
		system_settings = frappe.get_doc("System Settings")
		for key, val in global_defauls.items():
			system_settings[key] = val
		system_settings.ignore_mandatory = True
		system_settings.save()
