import frappe
from frappe.utils.business_modules import get_business_modules

from erpnext.hooks import business_modules
from erpnext.patches.v16_0.enable_business_modules_on_existing_companies import execute as run_patch
from erpnext.tests.utils import ERPNextTestSuite

FIELDNAMES = [m["fieldname"] for m in business_modules]


class TestCompanyBusinessModules(ERPNextTestSuite):
	"""The Modules Used section on Company."""

	def test_modules_are_registered_with_module_def_names(self):
		names = [m["module"] for m in get_business_modules() if m["app"] == "erpnext"]
		self.assertEqual(names, ["Stock", "Manufacturing", "Subcontracting", "Assets", "Projects", "POS"])
		# Names match the Module Def names. POS is the only one without a Module Def.
		for name in names:
			if name != "POS":
				self.assertTrue(frappe.db.exists("Module Def", name), name)

	def test_every_module_has_a_check_field_on_company(self):
		meta = frappe.get_meta("Company")
		for m in business_modules:
			field = meta.get_field(m["fieldname"])
			self.assertIsNotNone(field, m["fieldname"])
			self.assertEqual(field.fieldtype, "Check")
			self.assertEqual(field.label, m["module"])
			self.assertEqual(field.default, "0")

	def test_new_company_starts_with_every_module_off(self):
		# The user ticks what the company needs. The setup wizard sets them from its answers.
		company = frappe.new_doc("Company")
		for fieldname in FIELDNAMES:
			self.assertEqual(company.get(fieldname), 0, fieldname)

	def company_with_all_modules_on(self):
		company = frappe.get_doc("Company", "_Test Company")
		company.update({fieldname: 1 for fieldname in FIELDNAMES})
		company.save()
		return company

	def test_unticking_stock_unticks_manufacturing_and_subcontracting(self):
		company = self.company_with_all_modules_on()
		company.stock = 0
		company.save()
		self.assertEqual(company.manufacturing, 0)
		self.assertEqual(company.subcontracting, 0)

	def test_unticking_manufacturing_unticks_subcontracting_only(self):
		company = self.company_with_all_modules_on()
		company.manufacturing = 0
		company.save()
		self.assertEqual(company.stock, 1)
		self.assertEqual(company.subcontracting, 0)

	def test_manufacturing_cannot_be_on_without_stock(self):
		company = frappe.get_doc("Company", "_Test Company")
		company.update({"stock": 0, "manufacturing": 1, "subcontracting": 1})
		company.save()
		self.assertEqual(company.manufacturing, 0)
		self.assertEqual(company.subcontracting, 0)

	def test_patch_ticks_every_module_on_existing_companies(self):
		frappe.db.set_value("Company", "_Test Company", {f: 0 for f in FIELDNAMES})
		run_patch()
		values = frappe.db.get_value("Company", "_Test Company", FIELDNAMES, as_dict=True)
		self.assertTrue(all(values[f] == 1 for f in FIELDNAMES), values)

	def test_boot_sends_module_ticks_for_every_company(self):
		# The browser reads these to decide which module fields to hide on a form.
		from erpnext.startup.boot import boot_session, get_business_module_fields

		self.assertEqual(get_business_module_fields(), FIELDNAMES)

		bootinfo = frappe._dict(docs=[], sysdefaults=frappe._dict(), page_info=frappe._dict())
		boot_session(bootinfo)
		company = next(
			d for d in bootinfo.docs if d.get("doctype") == ":Company" and d.name == "_Test Company"
		)
		for fieldname in FIELDNAMES:
			self.assertIn(fieldname, company)
