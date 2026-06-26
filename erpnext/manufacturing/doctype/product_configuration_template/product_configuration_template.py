import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.manufacturing.doctype.product_configuration.formula import build_context, evaluate


class ProductConfigurationTemplate(Document):
	def validate(self):
		self.validate_variable_formulas()

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
