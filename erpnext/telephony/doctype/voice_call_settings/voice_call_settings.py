# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

ADMIN_ROLE = "System Manager"


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


def has_permission(doc: VoiceCallSettings, ptype: str | None = None, user: str | None = None) -> bool:
	"""Allow non-admin users to access only their own Voice Call Settings.

	Create is not scoped here because `before_insert` assigns the record to the creator."""
	user = user or frappe.session.user
	return ptype == "create" or is_admin(user) or doc.user == user


def get_permission_query_conditions(user: str | None = None) -> str | None:
	"""Restrict list views and queries to the user's own record for non-admin users."""
	user = user or frappe.session.user
	if is_admin(user):
		return None

	return f"`tabVoice Call Settings`.`user` = {frappe.db.escape(user)}"


def is_admin(user: str) -> bool:
	return ADMIN_ROLE in frappe.get_roles(user)
