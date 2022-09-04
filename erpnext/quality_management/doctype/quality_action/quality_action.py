# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class QualityAction(Document):
	def validate(self):
		self.status = "Open" if any([d.status == "Open" for d in self.resolutions]) else "Completed"
