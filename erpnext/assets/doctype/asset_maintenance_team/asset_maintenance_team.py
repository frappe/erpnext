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
