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

		existing_party_link = frappe.get_all('Party Link', {
			'primary_party': self.secondary_party
		}, pluck="primary_role")
		if existing_party_link:
			frappe.throw(_('{} {} is already linked with another {}')
				.format(self.secondary_role, self.secondary_party, existing_party_link[0]))

		existing_party_link = frappe.get_all('Party Link', {
			'secondary_party': self.primary_party
		}, pluck="primary_role")
		if existing_party_link:
			frappe.throw(_('{} {} is already linked with another {}')
				.format(self.primary_role, self.primary_party, existing_party_link[0]))
