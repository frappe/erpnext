# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class MedicalCode(Document):
	def autoname(self):
		self.name = self.medical_code_standard + " " + self.code
