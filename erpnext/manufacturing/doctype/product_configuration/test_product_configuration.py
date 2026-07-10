import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

TEMPLATE = "_Test PC Window"
FRAME = "_Test PC Frame"
GLASS = "_Test PC Glass"
WINDOW = "_Test PC Window Item"


class TestProductConfiguration(ERPNextTestSuite):
	def setUp(self):
		make_item(FRAME)
		make_item(GLASS)
		self.make_attribute("Width", "Float")
		self.make_attribute("Height", "Float")
		self.make_attribute("Material", "Select", "Wood\nAluminium")
		self.make_template()
		self.make_rules()

	def test_aggregates_duplicate_components(self):
		doc = self.make_config(2, 3, "Wood")
		self.assertEqual(self.components_map(doc), {FRAME: 7.0})

	def test_structured_condition_filters_rules(self):
		doc = self.make_config(2, 3, "Aluminium")
		self.assertEqual(self.components_map(doc), {FRAME: 1.0})

	def test_numeric_condition_and_derived_variable(self):
		doc = self.make_config(2000, 1, "Aluminium")
		components = self.components_map(doc)
		self.assertEqual(components[GLASS], 2.0)
		self.assertEqual(components[FRAME], 1.0)

	def test_variable_name_is_derived_and_validated(self):
		attribute = frappe.get_doc(
			{
				"doctype": "Product Configuration Attribute",
				"attribute_name": "Panel Count",
				"value_type": "Int",
			}
		).insert()
		self.assertEqual(attribute.variable_name, "panel_count")

		invalid = frappe.get_doc(
			{
				"doctype": "Product Configuration Attribute",
				"attribute_name": "Bad Attribute",
				"variable_name": "1 bad",
				"value_type": "Int",
			}
		)
		self.assertRaises(frappe.ValidationError, invalid.insert)

	def test_template_dashboard_links_rules(self):
		data = frappe.get_meta("Product Configuration Template").get_dashboard_data()
		self.assertEqual(data.fieldname, "template")
		items = [item for group in data.transactions for item in group.get("items", [])]
		self.assertIn("Product Configuration Rule", items)

	def test_configuration_dashboard_links_bom(self):
		data = frappe.get_meta("Product Configuration").get_dashboard_data()
		self.assertEqual(data.internal_links.get("BOM"), "bom")
		items = [item for group in data.transactions for item in group.get("items", [])]
		self.assertIn("BOM", items)

	def test_make_configuration_creates_and_calculates(self):
		template = frappe.get_doc("Product Configuration Template", TEMPLATE)

		fields = template.get_attribute_fields()
		material = next(field for field in fields if field["fieldname"] == "material")
		self.assertEqual(material["fieldtype"], "Select")
		self.assertEqual(material["options"], "Wood\nAluminium")

		name = template.make_configuration({"width": 2, "height": 3, "material": "Wood"})
		doc = frappe.get_doc("Product Configuration", name)
		self.assertEqual(doc.status, "Calculated")
		self.assertEqual(doc.title, TEMPLATE)
		self.assertEqual(self.components_map(doc), {FRAME: 7.0})

	def test_create_bom_guards_and_output(self):
		doc = self.make_config(2, 3, "Wood")
		self.assertRaises(frappe.ValidationError, doc.create_bom)

		make_item(WINDOW)
		frappe.db.set_value("Product Configuration Template", TEMPLATE, "configurable_item", WINDOW)

		uncalculated = frappe.get_doc(
			{
				"doctype": "Product Configuration",
				"template": TEMPLATE,
				"attribute_values": [{"attribute": "Width", "value": 1}],
			}
		).insert()
		self.assertRaises(frappe.ValidationError, uncalculated.create_bom)

		frappe.defaults.set_global_default("company", "_Test Company")
		bom = frappe.get_doc("BOM", doc.create_bom())
		self.assertEqual(bom.item, WINDOW)
		self.assertEqual(bom.docstatus, 0)
		self.assertEqual({row.item_code: row.qty for row in bom.items}, self.components_map(doc))
		self.assertEqual(doc.status, "BOM Created")
		self.assertEqual(doc.bom, bom.name)

	def test_calculate_requires_mandatory_values(self):
		frappe.db.set_value(
			"Product Configuration Template Attribute",
			{"parent": TEMPLATE, "attribute": "Width"},
			"mandatory",
			1,
		)
		doc = frappe.get_doc(
			{
				"doctype": "Product Configuration",
				"template": TEMPLATE,
				"attribute_values": [
					{"attribute": "Width", "value": ""},
					{"attribute": "Height", "value": 2},
				],
			}
		).insert()
		self.assertRaisesRegex(frappe.ValidationError, "Width", doc.calculate_components)

	def test_calculate_enforces_limits_and_select_options(self):
		frappe.db.set_value(
			"Product Configuration Template Attribute",
			{"parent": TEMPLATE, "attribute": "Width"},
			{"min_value": 100, "max_value": 5000},
		)
		doc = frappe.get_doc(
			{
				"doctype": "Product Configuration",
				"template": TEMPLATE,
				"attribute_values": [
					{"attribute": "Width", "value": 50},
					{"attribute": "Height", "value": 2},
					{"attribute": "Material", "value": "Plastic"},
				],
			}
		).insert()
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.calculate_components()
		self.assertIn("Width", str(caught.exception))
		self.assertIn("Material", str(caught.exception))

		good = self.make_config(200, 2, "Wood")
		self.assertEqual(good.status, "Calculated")

	def test_rule_summary_is_generated(self):
		rule = frappe.get_doc("Product Configuration Rule", {"rule_name": "Wood Frame", "template": TEMPLATE})
		self.assertEqual(rule.summary, "If Material == Wood: add CEILING(area) x _Test PC Frame")

		base = frappe.get_doc("Product Configuration Rule", {"rule_name": "Base Frame", "template": TEMPLATE})
		self.assertEqual(base.summary, "Always: add 1 x _Test PC Frame")

	def test_invalid_quantity_formula_blocks_rule(self):
		rule = frappe.get_doc(
			{
				"doctype": "Product Configuration Rule",
				"rule_name": "Broken",
				"template": TEMPLATE,
				"outputs": [{"component_item": FRAME, "uom": "Nos", "quantity_formula": "area *"}],
			}
		)
		self.assertRaises(frappe.ValidationError, rule.insert)

	def make_attribute(self, name, value_type, options=None):
		if not frappe.db.exists("Product Configuration Attribute", name):
			frappe.get_doc(
				{
					"doctype": "Product Configuration Attribute",
					"attribute_name": name,
					"value_type": value_type,
					"select_options": options,
				}
			).insert()

	def make_template(self):
		if frappe.db.exists("Product Configuration Template", TEMPLATE):
			return
		frappe.get_doc(
			{
				"doctype": "Product Configuration Template",
				"template_name": TEMPLATE,
				"attributes": [{"attribute": "Width"}, {"attribute": "Height"}, {"attribute": "Material"}],
				"variables": [{"variable_name": "area", "formula": "width * height"}],
			}
		).insert()

	def make_rules(self):
		self.make_rule(
			"Wood Frame",
			condition_logic="All conditions",
			conditions=[{"attribute": "Material", "operator": "==", "value": "Wood"}],
			outputs=[{"component_item": FRAME, "uom": "Nos", "quantity_formula": "CEILING(area)"}],
		)
		self.make_rule(
			"Base Frame",
			condition_logic="All conditions",
			outputs=[{"component_item": FRAME, "uom": "Nos", "quantity_formula": "1"}],
		)
		self.make_rule(
			"Large Glass",
			condition_logic="All conditions",
			conditions=[{"attribute": "Width", "operator": ">", "value": "1000"}],
			outputs=[{"component_item": GLASS, "uom": "Nos", "quantity_formula": "2"}],
		)

	def make_rule(self, rule_name, **kwargs):
		if frappe.db.exists("Product Configuration Rule", {"rule_name": rule_name, "template": TEMPLATE}):
			return
		frappe.get_doc(
			{"doctype": "Product Configuration Rule", "rule_name": rule_name, "template": TEMPLATE, **kwargs}
		).insert()

	def make_config(self, width, height, material):
		doc = frappe.get_doc(
			{
				"doctype": "Product Configuration",
				"template": TEMPLATE,
				"attribute_values": [
					{"attribute": "Width", "value": width},
					{"attribute": "Height", "value": height},
					{"attribute": "Material", "value": material},
				],
			}
		).insert()
		doc.calculate_components()
		return doc

	def components_map(self, doc):
		return {row.component_item: row.qty for row in doc.components}
