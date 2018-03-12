from __future__ import unicode_literals
import frappe


def execute():
	subscriptions = frappe.db.sql('SELECT name from `tabSubscription`', as_dict=True)

	for subscription in subscriptions:
		doc = frappe.get_doc('Subscription', subscription['name'])
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc('Subscription', subscription['name'], force=True, ignore_permissions=True)
