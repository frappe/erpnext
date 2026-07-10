import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from erpnext.manufacturing.doctype.product_configuration.formula import build_context, evaluate


class ProductConfigurationTemplate(Document):
	def validate(self):
		self.validate_variable_formulas()

	@frappe.whitelist()
	def make_configuration(self, values: dict | str) -> str:
		values = frappe.parse_json(values) or {}
		config = frappe.new_doc("Product Configuration")
		config.template = self.name
		for row in self.attributes:
			config.append(
				"attribute_values",
				{"attribute": row.attribute, "value": values.get(row.variable_name, row.default_value)},
			)
		config.insert()
		config.calculate_components()
		config.save()
		return config.name

	@frappe.whitelist()
	def get_attribute_fields(self) -> list[dict]:
		masters = attribute_masters([row.attribute for row in self.attributes])
		return [dialog_field(row, masters[row.attribute]) for row in self.attributes]

	def validate_variable_formulas(self):
		if not self.variables:
			return

		context = build_context(self.dummy_attribute_values())
		for variable in self.variables:
			result = evaluate(variable.formula, context)
			if not result["ok"]:
				frappe.throw(
					_("Formula for variable {0} is invalid: {1}").format(
						variable.variable_name, result["error"]
					)
				)
			context[variable.variable_name] = result["value"]

	def dummy_attribute_values(self) -> dict:
		attributes = frappe.get_all(
			"Product Configuration Attribute",
			filters={"name": ["in", [row.attribute for row in self.attributes]]},
			fields=["variable_name"],
		)
		return {row.variable_name: 1.0 for row in attributes}


def attribute_masters(names: list[str]) -> dict:
	rows = frappe.get_all(
		"Product Configuration Attribute",
		filters={"name": ["in", names]},
		fields=["name", "value_type", "select_options", "default_value", "description"],
	)
	return {row.name: row for row in rows}


def dialog_field(row, master) -> dict:
	return {
		"fieldname": row.variable_name,
		"label": row.attribute,
		"fieldtype": master.value_type or "Data",
		"options": master.select_options,
		"default": row.default_value or master.default_value,
		"reqd": cint(row.mandatory),
		"description": master.description,
	}
