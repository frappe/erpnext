# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

# imports - module imports
import frappe


def execute():
	"""
	Delete the "Land Unit" doc if exists from "Desktop Icon" doctype
	"""
	try:
		doc = frappe.get_doc('Desktop Icon', {'standard': 1, 'module_name': 'Land Unit'})
		frappe.delete_doc('Desktop Icon', doc.name)
	except frappe.ValidationError:
		# The 'Land Unit' doc doesn't exist, nothing to do
		pass
