# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("setup", "doctype", "country")

	from frappe.country_info import get_all
	
	for name, country in get_all().iteritems():
		frappe.set_value("Country", name, "code", country.get("code"))