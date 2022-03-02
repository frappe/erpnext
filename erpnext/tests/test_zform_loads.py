""" dumb test to check all function calls on known form loads """

import unittest

import frappe
from frappe.desk.form.load import getdoc


class TestFormLoads(unittest.TestCase):

	def test_load(self):
		erpnext_modules = frappe.get_all("Module Def", filters={"app_name": "erpnext"}, pluck="name")
		doctypes = frappe.get_all("DocType", {"istable": 0, "issingle": 0, "is_virtual": 0, "module": ("in", erpnext_modules)}, pluck="name")

		for doctype in doctypes:
			last_doc = frappe.db.get_value(doctype, {}, "name", order_by="modified desc")
			if not last_doc:
				continue
			with self.subTest(msg=f"Loading {doctype} - {last_doc}", doctype=doctype, last_doc=last_doc):
				try:
					# reset previous response
					frappe.response = frappe._dict({"docs":[]})
					frappe.response.docinfo = None

					getdoc(doctype, last_doc)
				except Exception as e:
					self.fail(f"Failed to load {doctype} - {last_doc}: {e}")

				self.assertTrue(frappe.response.docs, msg=f"expected document in reponse, found: {frappe.response.docs}")
				self.assertTrue(frappe.response.docinfo, msg=f"expected docinfo in reponse, found: {frappe.response.docinfo}")
