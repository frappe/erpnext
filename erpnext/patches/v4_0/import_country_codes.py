# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.geo.country_info import get_all
from frappe.utils.install import import_country_and_currency

from six import iteritems

def execute():
	frappe.reload_doc("setup", "doctype", "country")
	import_country_and_currency()
	for name, country in iteritems(get_all()):
		frappe.set_value("Country", name, "code", country.get("code"))