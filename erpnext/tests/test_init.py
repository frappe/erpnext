from erpnext import encode_company_abbr
from erpnext.tests.utils import ERPNextTestSuite


class TestInit(ERPNextTestSuite):
	def test_encode_company_abbr(self):
		abbr = "NFECT"

		names = [
			"Warehouse Name",
			"ERPNext Foundation India",
			f"Gold - Member - {abbr}",
			f" - {abbr}",
			"ERPNext - Foundation - India",
			f"ERPNext Foundation India - {abbr}",
			f"No-Space-{abbr}",
			"- Warehouse",
		]

		expected_names = [
			f"Warehouse Name - {abbr}",
			f"ERPNext Foundation India - {abbr}",
			f"Gold - Member - {abbr}",
			f" - {abbr}",
			f"ERPNext - Foundation - India - {abbr}",
			f"ERPNext Foundation India - {abbr}",
			f"No-Space-{abbr} - {abbr}",
			f"- Warehouse - {abbr}",
		]

		for i in range(len(names)):
			enc_name = encode_company_abbr(names[i], abbr=abbr)
			self.assertTrue(
				enc_name == expected_names[i],
				f"{enc_name} is not same as {expected_names[i]}",
			)

	def test_translation_files(self):
		from frappe.tests.test_translate import verify_translation_files

		verify_translation_files("erpnext")

	def test_patches(self):
		from frappe.tests.test_patches import check_patch_files

		check_patch_files("erpnext")

	def test_no_unrendered_title_templates(self):
		import frappe

		modules = frappe.get_all("Module Def", filters={"app_name": "erpnext"}, pluck="name")
		for doctype in frappe.get_all("DocType", filters={"module": ("in", modules)}, pluck="name"):
			meta = frappe.get_meta(doctype)
			field = meta.get_field("title")
			if not field or not field.default or "{" not in field.default:
				continue

			self.assertEqual(
				meta.title_field,
				"title",
				f"{doctype}: title default {field.default!r} is stored verbatim because "
				"Document.set_title_field() only renders it when title_field is 'title'",
			)
