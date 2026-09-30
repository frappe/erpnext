# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series


class Campaign(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.crm.doctype.campaign_email_schedule.campaign_email_schedule import (
			CampaignEmailSchedule,
		)

		campaign_name: DF.Data
		campaign_schedules: DF.Table[CampaignEmailSchedule]
		description: DF.Text | None
		naming_series: DF.Literal["SAL-CAM-.YYYY.-"]
	# end: auto-generated types

	def after_insert(self):
		self.sync_utm_campaign()

	def on_change(self):
		self.sync_utm_campaign()

	def sync_utm_campaign(self):
		mc = self.get_utm_campaign_mirror()
		mc.campaign_description = self.description
		# link by the document name, which differs from campaign_name when a naming series is used
		mc.crm_campaign = self.name
		mc.save(ignore_permissions=True)

	def get_utm_campaign_mirror(self):
		# the mirror already linked to this Campaign, if any (survives campaign_name edits)
		if owned := frappe.db.get_value("UTM Campaign", {"crm_campaign": self.name}):
			return frappe.get_doc("UTM Campaign", owned)

		# reuse a same-named mirror only when it isn't already owned by another Campaign,
		# otherwise two Campaigns sharing a display name would hijack each other's mirror
		if frappe.db.exists("UTM Campaign", self.campaign_name):
			same_name = frappe.get_doc("UTM Campaign", self.campaign_name)
			if not same_name.crm_campaign or same_name.crm_campaign == self.name:
				return same_name

		# create a fresh mirror, keeping its name unique when the display name is taken
		mc = frappe.new_doc("UTM Campaign")
		mc.name = self.name if frappe.db.exists("UTM Campaign", self.campaign_name) else self.campaign_name
		return mc

	def autoname(self):
		if frappe.defaults.get_global_default("campaign_naming_by") != "Naming Series":
			self.name = self.campaign_name
		else:
			set_name_by_naming_series(self)
