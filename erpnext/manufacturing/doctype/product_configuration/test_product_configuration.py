import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

TEMPLATE = "_Test PC Window"
FRAME = "_Test PC Frame"
GLASS = "_Test PC Glass"


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

	def test_expression_condition_and_derived_variable(self):
		doc = self.make_config(2000, 1, "Aluminium")
		components = self.components_map(doc)
		self.assertEqual(components[GLASS], 2.0)
		self.assertEqual(components[FRAME], 1.0)

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
			condition_logic="Expression",
			condition_expression="width > 1000",
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
