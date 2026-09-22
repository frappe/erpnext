# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""What ERPNext hands the desk v2 build: a published name, a Tailwind preset, a declaration."""

import json
import os

import frappe
from frappe.tests import UnitTestCase

APP = frappe.get_app_path("erpnext")


class TestDeskV2Publishing(UnitTestCase):
	def test_the_published_name_points_at_a_file(self):
		targets = frappe.get_hooks("import_map", app_name="erpnext", default={}).get("erpnext/lib")

		self.assertTrue(targets, "hooks.py publishes no erpnext/lib")
		self.assertTrue(os.path.isfile(os.path.join(APP, targets[-1])))

	def test_the_preset_is_an_es_module_that_only_extends(self):
		with open(os.path.join(APP, "frontend", "tailwind.preset.js")) as handle:
			source = handle.read()

		self.assertIn("export default", source)
		self.assertNotIn("module.exports", source)
		self.assertIn("extend", source)
		self.assertNotIn("safelist", source)

	def test_the_declaration_holds_dependencies_only(self):
		with open(os.path.join(APP, "desk.package.json")) as handle:
			declaration = json.load(handle)

		self.assertEqual(list(declaration), ["dependencies"])
		self.assertIn("vue", declaration["dependencies"])
