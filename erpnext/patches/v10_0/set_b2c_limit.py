# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("regional", "doctype", "gst_settings")
	frappe.reload_doc("accounting", "doctype", "gst_account")
	gst_settings = frappe.get_doc("GST Settings")
	gst_settings.b2c_limit = 250000
	gst_settings.save()
