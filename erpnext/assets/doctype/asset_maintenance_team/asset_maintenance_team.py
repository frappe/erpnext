# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssetMaintenanceTeam(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.maintenance_team_member.maintenance_team_member import (
			MaintenanceTeamMember,
		)

		company: DF.Link
		maintenance_manager: DF.Link | None
		maintenance_manager_name: DF.ReadOnly | None
		maintenance_team_members: DF.Table[MaintenanceTeamMember]
		maintenance_team_name: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_unique_members()
		self.validate_manager_is_member()
		self.validate_removed_members_have_no_tasks()

	def validate_unique_members(self):
		members = set()
		for row in self.maintenance_team_members:
			if row.team_member in members:
				frappe.throw(
					_("Row #{0}: {1} is already a member of this team.").format(
						row.idx, frappe.bold(row.team_member)
					)
				)
			members.add(row.team_member)

	def validate_manager_is_member(self):
		if self.maintenance_manager and self.maintenance_manager not in self.get_members():
			frappe.throw(
				_("Maintenance Manager {0} must be a member of the team.").format(
					frappe.bold(self.maintenance_manager)
				)
			)

	def validate_removed_members_have_no_tasks(self):
		previous = self.get_doc_before_save()
		removed_members = previous.get_members() - self.get_members() if previous else set()
		if not removed_members:
			return

		assignees = frappe.get_all(
			"Asset Maintenance Task",
			filters={
				"parenttype": "Asset Maintenance",
				"parent": ("in", self.get_asset_maintenances()),
				"assign_to": ("in", removed_members),
				"maintenance_status": ("!=", "Cancelled"),
			},
			pluck="assign_to",
			distinct=True,
		)
		if assignees:
			frappe.throw(
				_("Reassign the maintenance tasks of {0} before removing them from the team.").format(
					", ".join(frappe.bold(assignee) for assignee in assignees)
				)
			)

	def get_members(self) -> set[str]:
		return {row.team_member for row in self.maintenance_team_members}

	def get_asset_maintenances(self) -> list[str]:
		return frappe.get_all("Asset Maintenance", filters={"maintenance_team": self.name}, pluck="name")
