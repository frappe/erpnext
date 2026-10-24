# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class VoiceCallSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_busy_message: DF.Data | None
		agent_unavailable_message: DF.Data | None
		call_receiving_device: DF.Literal["Computer", "Phone"]
		greeting_message: DF.Data | None
		user: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.set_user_for_restricted_creator()

	def set_user_for_restricted_creator(self):
		"""Users who may not pick the user create their own settings."""
		if self.flags.ignore_permissions or self.has_permlevel_access_to("user", permission_type="write"):
			return

		self.user = frappe.session.user
		self.flags.ignore_permlevel_for_fields = ["user"]
