import frappe
from frappe.model.document import Document


class ProductConfigurationAttribute(Document):
	def validate(self):
		if not self.variable_name:
			self.variable_name = frappe.scrub(self.attribute_name)
