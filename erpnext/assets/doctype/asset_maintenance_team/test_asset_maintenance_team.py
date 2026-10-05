# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAssetMaintenanceTeam(ERPNextTestSuite):
	def test_member_can_join_several_teams_but_only_once_per_team(self):
		make_team("Night Shift", ["marcus@abc.com", "thalia@abc.com"])
		second = make_team("Weekend Shift", ["marcus@abc.com"])
		self.assertEqual(second.maintenance_team_members[0].team_member, "marcus@abc.com")

		self.assertRaises(
			frappe.ValidationError, make_team, "Duplicate Shift", ["thalia@abc.com", "thalia@abc.com"]
		)


def make_team(name: str, members: list[str]):
	return frappe.get_doc(
		{
			"doctype": "Asset Maintenance Team",
			"maintenance_team_name": name,
			"maintenance_manager": members[0],
			"company": "_Test Company",
			"maintenance_team_members": [
				{"team_member": member, "maintenance_role": "Technician"} for member in members
			],
		}
	).insert()
