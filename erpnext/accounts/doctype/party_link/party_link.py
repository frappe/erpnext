# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class PartyLink(Document):
	def validate(self):
		if self.primary_role not in ['Customer', 'Supplier']:
			frappe.throw(_("Allowed primary roles are 'Customer' and 'Supplier'. Please select one of these roles only."),
				title=_("Invalid Primary Role"))
