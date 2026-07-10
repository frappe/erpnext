import frappe
from frappe import _
from frappe.model.document import Document


class ProductConfigurationAttribute(Document):
	def validate(self):
		if not self.variable_name:
			self.variable_name = frappe.scrub(self.attribute_name)
		if not self.variable_name.isidentifier():
			frappe.throw(
				_(
					"Variable Name {0} must contain only letters, digits and underscores, and cannot start with a digit"
				).format(frappe.bold(self.variable_name))
			)
