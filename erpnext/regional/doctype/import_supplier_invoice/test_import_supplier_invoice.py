# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import get_country
from erpnext.tests.utils import ERPNextTestSuite


class TestImportSupplierInvoice(ERPNextTestSuite):
	"""The importer requires a default stock UOM and resolves country codes from the file."""

	@ERPNextTestSuite.change_settings("Stock Settings", {"stock_uom": ""})
	def test_validate_requires_a_default_uom(self):
		doc = frappe.new_doc("Import Supplier Invoice")
		self.assertRaises(frappe.ValidationError, doc.validate)

	@ERPNextTestSuite.change_settings("Stock Settings", {"stock_uom": "Nos"})
	def test_validate_passes_with_a_default_uom(self):
		frappe.new_doc("Import Supplier Invoice").validate()

	def test_get_country_resolves_a_known_code(self):
		country = frappe.get_all("Country", filters={"code": ["!=", ""]}, fields=["name", "code"], limit=1)[0]
		self.assertEqual(get_country(country.code), country.name)

	def test_get_country_rejects_an_unknown_code(self):
		self.assertRaises(frappe.ValidationError, get_country, "__no_such_country_code__")
