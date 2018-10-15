import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	""" copy subscribe field to customer """
	frappe.reload_doc("accounts","doctype","subscription")

	if frappe.db.exists("DocType", "Subscriber"):
		if frappe.db.has_column('Subscription','subscriber'):
			frappe.db.sql("""
				update `tabSubscription` s1
				set customer=(select customer from tabSubscriber where name=s1.subscriber)
			""")

		frappe.delete_doc("DocType", "Subscriber")