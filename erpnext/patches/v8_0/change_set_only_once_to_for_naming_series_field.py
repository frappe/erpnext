from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET set_only_once = 1
		WHERE fieldname = 'naming_series';
		"""
	)