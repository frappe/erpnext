# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


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

	pass
