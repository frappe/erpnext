# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CRMSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_lead_duplication_based_on_emails: DF.Check
		auto_creation_of_contact: DF.Check
		campaign_naming_by: DF.Literal["Campaign Name", "Naming Series"]
		carry_forward_communication_and_comments: DF.Check
		close_opportunity_after_days: DF.Int
		default_valid_till: DF.Data | None
		enable_opportunity_creation_from_contact_us: DF.Check
		update_timestamp_on_new_communication: DF.Check
	# end: auto-generated types

	def validate(self):
		frappe.db.set_default("campaign_naming_by", self.get("campaign_naming_by", ""))
		self.validate_enable_opportunity_creation_from_contact_us()

	def validate_enable_opportunity_creation_from_contact_us(self):
		contact_disabled = frappe.get_single_value("Contact Us Settings", "is_disabled")

		if self.enable_opportunity_creation_from_contact_us and contact_disabled:
			frappe.throw(
				_(
					"Cannot enable Opportunity creation from Contact Us because the Contact Us form is disabled."
				)
			)
