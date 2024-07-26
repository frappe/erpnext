import unittest

import frappe

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier


class TestWebsite(unittest.TestCase):
	def test_permission_for_custom_doctype(self):
		create_user("Supplier 1", "supplier1@gmail.com")
		create_user("Supplier 2", "supplier2@gmail.com")

		supplier1 = create_supplier(supplier_name="Supplier1")
		supplier2 = create_supplier(supplier_name="Supplier2")
		supplier1.append("portal_users", {"user": "supplier1@gmail.com"})
		supplier1.save()
		supplier2.append("portal_users", {"user": "supplier2@gmail.com"})
		supplier2.save()

		po1 = create_purchase_order(supplier="Supplier1")
		po2 = create_purchase_order(supplier="Supplier2")

		create_custom_doctype()
		create_webform()
		create_order_assignment(supplier="Supplier1", po=po1.name)
		create_order_assignment(supplier="Supplier2", po=po2.name)

		frappe.set_user("Administrator")
		# checking if data consist of all order assignment of Supplier1 and Supplier2
		self.assertTrue("Supplier1" and "Supplier2" in [data.supplier for data in get_data()])

		frappe.set_user("supplier1@gmail.com")
		# checking if data only consist of order assignment of Supplier1
		self.assertTrue("Supplier1" in [data.supplier for data in get_data()])
		self.assertFalse([data.supplier for data in get_data() if data.supplier != "Supplier1"])

		frappe.set_user("supplier2@gmail.com")
		# checking if data only consist of order assignment of Supplier2
		self.assertTrue("Supplier2" in [data.supplier for data in get_data()])
		self.assertFalse([data.supplier for data in get_data() if data.supplier != "Supplier2"])

		frappe.set_user("Administrator")


def get_data():
	webform_list_contexts = frappe.get_hooks("webform_list_context")
	if webform_list_contexts:
		context = frappe._dict(frappe.get_attr(webform_list_contexts[0])("Buying") or {})
	kwargs = dict(doctype="Order Assignment", order_by="creation desc")
	return context.get_list(**kwargs)


def create_user(name, email):
	frappe.get_doc(
		{
			"doctype": "User",
			"send_welcome_email": 0,
			"user_type": "Website User",
			"first_name": name,
			"email": email,
			"roles": [{"doctype": "Has Role", "role": "Supplier"}],
		}
	).insert(ignore_if_duplicate=True)


def create_custom_doctype():
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": "Order Assignment",
			"module": "Buying",
			"custom": 1,
			"autoname": "field:po",
			"fields": [
				{"label": "PO", "fieldname": "po", "fieldtype": "Link", "options": "Purchase Order"},
				{
					"label": "Supplier",
					"fieldname": "supplier",
					"fieldtype": "Data",
					"fetch_from": "po.supplier",
				},
			],
			"permissions": [
				{
					"create": 1,
					"delete": 1,
					"email": 1,
					"export": 1,
					"print": 1,
					"read": 1,
					"report": 1,
					"role": "System Manager",
					"share": 1,
					"write": 1,
				},
				{"read": 1, "role": "Supplier"},
			],
		}
	).insert(ignore_if_duplicate=True)


def create_webform():
	frappe.get_doc(
		{
			"doctype": "Web Form",
			"module": "Buying",
			"title": "SO Schedule",
			"route": "so-schedule",
			"doc_type": "Order Assignment",
			"web_form_fields": [
				{
					"doctype": "Web Form Field",
					"fieldname": "po",
					"fieldtype": "Link",
					"options": "Purchase Order",
					"label": "PO",
				},
				{
					"doctype": "Web Form Field",
					"fieldname": "supplier",
					"fieldtype": "Data",
					"label": "Supplier",
				},
			],
		}
	).insert(ignore_if_duplicate=True)


def create_order_assignment(supplier, po):
	frappe.get_doc(
		{
			"doctype": "Order Assignment",
			"po": po,
			"supplier": supplier,
		}
	).insert(ignore_if_duplicate=True)
