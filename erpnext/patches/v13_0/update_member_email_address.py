# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	"""add value to email_id column from email"""

	if frappe.db.has_column("Member", "email"):
		# Get all members
		for member in frappe.db.get_all("Member", pluck="name"):
			# Check if email_id already exists
			if not frappe.db.get_value("Member", member, "email_id"):
				# fetch email id from the user linked field email
				email = frappe.db.get_value("Member", member, "email")

				# Set the value for it
				frappe.db.set_value("Member", member, "email_id", email)

	if frappe.db.exists("DocType", "Membership Settings"):
		rename_field("Membership Settings", "enable_auto_invoicing", "enable_invoicing")
