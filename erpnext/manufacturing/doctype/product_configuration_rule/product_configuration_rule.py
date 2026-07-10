import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.manufacturing.doctype.product_configuration.formula import evaluate
from erpnext.manufacturing.doctype.product_configuration.product_configuration import build_dummy_context


class ProductConfigurationRule(Document):
	def validate(self):
		self.validate_formulas()
		self.summary = self.build_summary()

	def build_summary(self) -> str:
		outputs = ", ".join(f"{output.quantity_formula} x {output.component_item}" for output in self.outputs)
		if not self.conditions:
			return _("Always: add {0}").format(outputs)

		joiner = _(" and ") if self.condition_logic == "All conditions" else _(" or ")
		conditions = joiner.join(f"{row.attribute} {row.operator} {row.value}" for row in self.conditions)
		return _("If {0}: add {1}").format(conditions, outputs)

	def validate_formulas(self):
		context = build_dummy_context(self.template)

		for output in self.outputs:
			self.assert_valid_formula(
				output.quantity_formula, context, _("Quantity formula for {0}").format(output.component_item)
			)

	def assert_valid_formula(self, expression, context, label):
		result = evaluate(expression, context)
		if not result["ok"]:
			frappe.throw(_("{0} is invalid: {1}").format(label, result["error"]))
