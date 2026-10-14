# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.assets.doctype.asset_maintenance.test_asset_maintenance import get_maintenance_tasks
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetMaintenanceTeam(ERPNextTestSuite):
	def test_member_can_join_several_teams_but_only_once_per_team(self):
		make_team("Night Shift", ["marcus@abc.com", "thalia@abc.com"])
		second = make_team("Weekend Shift", ["marcus@abc.com"])
		self.assertEqual(second.maintenance_team_members[0].team_member, "marcus@abc.com")

		self.assertRaises(
			frappe.ValidationError, make_team, "Duplicate Shift", ["thalia@abc.com", "thalia@abc.com"]
		)

	def test_manager_must_be_a_member_and_assignees_cannot_be_removed(self):
		team = frappe.get_doc("Asset Maintenance Team", "Team Awesome")
		team.maintenance_manager = "test@example.com"
		self.assertRaises(frappe.ValidationError, team.save)

		make_asset_maintenance("Team Awesome")
		team.reload()
		team.maintenance_team_members = [
			row for row in team.maintenance_team_members if row.team_member != "thalia@abc.com"
		]
		self.assertRaises(frappe.ValidationError, team.save)

		team.reload()
		team.maintenance_team_members = [
			row for row in team.maintenance_team_members if row.team_member != "mathias@abc.com"
		]
		team.save()


def make_asset_maintenance(team: str):
	receipt = make_purchase_receipt(item_code="Photocopier", qty=1, rate=100000.0, location="Test Location")
	asset = frappe.get_doc("Asset", {"purchase_receipt": receipt.name})
	asset.available_for_use_date = nowdate()
	asset.purchase_date = nowdate()
	asset.save()
	return frappe.get_doc(
		{
			"doctype": "Asset Maintenance",
			"asset_name": asset.name,
			"maintenance_team": team,
			"company": "_Test Company",
			"asset_maintenance_tasks": get_maintenance_tasks(),
		}
	).insert()


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
