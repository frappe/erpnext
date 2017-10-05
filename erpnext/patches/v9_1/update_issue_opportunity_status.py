# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ("Issue", "Opportunity"):
		frappe.reload_doctype(doctype)

		update_documents_status(doctype)
		update_email_alerts_conditions(doctype)

def update_documents_status(doctype):
	"""
		Update Issue and Opportunity Status `Open` to `Unreplied`
		& `Replied` to `Open`
	"""
	frappe.db.sql("""UPDATE `tab{0}`
		SET status = CASE
			WHEN status='Open' THEN 'Unreplied'
			WHEN status='Replied' THEN 'Open'
		END""".format(doctype))

def update_email_alerts_conditions(doctype):
	"""
		Check and update the conditions for the doctype's email alerts
	"""
	email_alerts = frappe.get_all("Email Alert", filters=dict(
		document_type=doctype,
		condition=("like", "%status%")
	))

	for alert in email_alerts:
		email_alert = frappe.get_doc("Email Alert", alert.name)
		if email_alert.condition and "Open" in email_alert.condition:
			email_alert.condition = email_alert.condition.replace("Open", "Unreplied")
		if email_alert.condition and "Replied" in email_alert.condition:
			email_alert.condition = email_alert.condition.replace("Replied", "Open")

		email_alert.save(ignore_permissions=True)