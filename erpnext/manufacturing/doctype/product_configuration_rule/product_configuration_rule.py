import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.manufacturing.doctype.product_configuration.formula import evaluate
from erpnext.manufacturing.doctype.product_configuration.product_configuration import build_dummy_context


class ProductConfigurationRule(Document):
	def validate(self):
		self.validate_formulas()

	def validate_formulas(self):
		context = build_dummy_context(self.template)

		if self.condition_logic == "Expression":
			self.assert_valid_formula(self.condition_expression, context, _("Condition expression"))

		for output in self.outputs:
			self.assert_valid_formula(
				output.quantity_formula, context, _("Quantity formula for {0}").format(output.component_item)
			)

	def assert_valid_formula(self, expression, context, label):
		result = evaluate(expression, context)
		if not result["ok"]:
			frappe.throw(_("{0} is invalid: {1}").format(label, result["error"]))
