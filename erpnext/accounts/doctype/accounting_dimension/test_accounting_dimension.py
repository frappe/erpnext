# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unicodedata

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountingDimension(ERPNextTestSuite):
	def test_dimension_against_sales_invoice(self):
		si = create_sales_invoice(do_not_save=1)

		si.location = "Block 1"
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"department": "_Test Department - _TC",
				"location": "Block 1",
			},
		)

		si.save()
		si.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"})

		self.assertEqual(gle.get("department"), "_Test Department - _TC")

	def test_dimension_against_journal_entry(self):
		je = make_journal_entry("Sales - _TC", "Sales Expenses - _TC", 500, save=False)
		je.accounts[0].update({"department": "_Test Department - _TC"})
		je.accounts[1].update({"department": "_Test Department - _TC"})

		je.accounts[0].update({"location": "Block 1"})
		je.accounts[1].update({"location": "Block 1"})

		je.save()
		je.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales - _TC"})
		gle1 = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales Expenses - _TC"})
		self.assertEqual(gle.get("department"), "_Test Department - _TC")
		self.assertEqual(gle1.get("department"), "_Test Department - _TC")

	def test_mandatory(self):
		location = frappe.get_doc("Accounting Dimension", "Location")
		location.dimension_defaults[0].mandatory_for_bs = True
		location.save()

		si = create_sales_invoice(do_not_save=1)
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"location": "",
			},
		)

		si.save()
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_accented_label_generates_ascii_fieldname(self):
		doc = frappe.new_doc("Accounting Dimension")
		doc.label = "Département"
		doc.set_fieldname_and_label()
		self.assertEqual(doc.fieldname, "departement")

	def test_various_diacritics_stripped_from_fieldname(self):
		test_cases = [
			("München", "munchen"),
			("España", "espana"),
			("Naïve", "naive"),
			("Zürich", "zurich"),
			("Îles", "iles"),
			("Çà", "ca"),
		]

		for label, expected_fieldname in test_cases:
			self.assertEqual(self._get_fieldname(label), expected_fieldname)

	def test_fieldname_generation_with_spaces_and_hyphens(self):
		test_cases = [
			("Département Region", "departement_region"),
			("Zone-Test", "zone_test"),
			("Café Paris", "cafe_paris"),
			("Test-Field-Name", "test_field_name"),
		]

		for label, expected_fieldname in test_cases:
			self.assertEqual(self._get_fieldname(label), expected_fieldname)

	def test_fieldname_generation_with_mixed_special_chars(self):
		test_cases = [
			("Café-Restaurant München", "cafe_restaurant_munchen"),
			("Área de Vendas", "area_de_vendas"),
			("Coût & Prix", "cout_prix"),
		]

		for label, expected_fieldname in test_cases:
			self.assertEqual(self._get_fieldname(label), expected_fieldname)

	def test_fieldname_validation_rejects_diacritics_without_stripping(self):
		from frappe.database.schema import validate_column_name
		from frappe.exceptions import InvalidColumnName

		validate_column_name("departement")
		validate_column_name("test_field")

		with self.assertRaises(InvalidColumnName):
			validate_column_name("département")

		with self.assertRaises(InvalidColumnName):
			validate_column_name("münchen")

	def test_set_fieldname_and_label_method(self):
		test_cases = [
			("Département", "departement"),
			("Test Label", "test_label"),
			("Café", "cafe"),
			("Ñoño", "nono"),
			("Ångström", "angstrom"),
		]

		for label, expected_fieldname in test_cases:
			self.assertEqual(self._get_fieldname(label), expected_fieldname)

	def test_client_server_fieldname_consistency(self):
		"""Test that client-side JS and server-side Python generate the same fieldname."""
		test_cases = [
			("Département", "departement"),
			("Département Region", "departement_region"),
			("Zone-Test", "zone_test"),
			("Café-Restaurant München", "cafe_restaurant_munchen"),
			("Área de Vendas", "area_de_vendas"),
		]

		for label, expected_fieldname in test_cases:
			ascii_label = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
			client_fieldname = ascii_label.replace(" ", "_").replace("-", "_").lower()
			server_fieldname = self._get_fieldname(label)
			self.assertEqual(client_fieldname, server_fieldname)

	def test_edge_cases_fieldname_generation(self):
		test_cases = [
			("  Test  ", "__test__"),
			("Test--Field", "test__field"),
			("Test  Field", "test__field"),
			("-Test-", "_test_"),
			("Zone-123", "zone_123"),
			("Test-1ère", "test_1ere"),
			("Test@", "test"),
		]

		for label, expected_fieldname in test_cases:
			self.assertEqual(self._get_fieldname(label), expected_fieldname)

	def test_empty_fieldname_from_special_chars(self):
		"""Test that labels with only special characters produce fieldname with special chars."""
		doc = frappe.new_doc("Accounting Dimension")
		doc.label = "!!!"
		doc.set_fieldname_and_label()
		self.assertEqual(doc.fieldname, "!!!")

	def _get_fieldname(self, label):
		doc = frappe.new_doc("Accounting Dimension")
		doc.label = label
		doc.set_fieldname_and_label()
		return doc.fieldname

	def tearDown(self):
		disable_dimension()
		frappe.flags.accounting_dimensions_details = None
		frappe.flags.dimension_filter_map = None


def create_dimension():
	frappe.set_user("Administrator")

	if not frappe.db.exists("Accounting Dimension", {"document_type": "Department"}):
		dimension = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"document_type": "Department",
			}
		)
		dimension.append(
			"dimension_defaults",
			{
				"company": "_Test Company",
				"reference_document": "Department",
				"default_dimension": "_Test Department - _TC",
			},
		)
		dimension.insert()
		dimension.save()
	else:
		dimension = frappe.get_doc("Accounting Dimension", "Department")
		dimension.disabled = 0
		dimension.save()

	if not frappe.db.exists("Accounting Dimension", {"document_type": "Location"}):
		dimension1 = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"document_type": "Location",
			}
		)

		dimension1.append(
			"dimension_defaults",
			{
				"company": "_Test Company",
				"reference_document": "Location",
				"default_dimension": "Block 1",
			},
		)

		dimension1.insert()
		dimension1.save()
	else:
		dimension1 = frappe.get_doc("Accounting Dimension", "Location")
		dimension1.disabled = 0
		dimension1.save()


def disable_dimension():
	dimension1 = frappe.get_doc("Accounting Dimension", "Department")
	dimension1.disabled = 1
	dimension1.save()

	dimension2 = frappe.get_doc("Accounting Dimension", "Location")
	dimension2.disabled = 1
	dimension2.save()
