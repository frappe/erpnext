import frappe
from frappe import _

def execute():
	frappe.db.sql("""
		UPDATE `tabDesktop Icon`
		SET
			`module_name`='Help', `label`=%s
		WHERE
			`module_name`='Learn' AND
			`standard`=1
		""", _('Help'))