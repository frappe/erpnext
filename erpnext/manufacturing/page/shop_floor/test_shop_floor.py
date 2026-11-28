import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_to_date, now

from erpnext.manufacturing.doctype.job_card.test_job_card import (
	make_jc_review_employee,
	make_jc_review_job_cards,
	make_jc_review_workstation,
)
from erpnext.manufacturing.page.shop_floor import shop_floor
from erpnext.tests.utils import ERPNextTestSuite


class TestShopFloor(ERPNextTestSuite):
	def make_floor(self, lines):
		floor = frappe.get_doc(
			{
				"doctype": "Plant Floor",
				"floor_name": f"_Test Floor {frappe.generate_hash(length=6)}",
				"company": "_Test Company",
			}
		).insert()
		workstations = {}
		for line, count in lines.items():
			for sequence in range(count, 0, -1):
				workstation = make_jc_review_workstation()
				frappe.db.set_value(
					"Workstation",
					workstation,
					{"plant_floor": floor.name, "production_line": line, "line_sequence": sequence},
				)
				workstations.setdefault(line, []).insert(0, workstation)
		return floor.name, workstations

	def test_floor_groups_workstations_by_line_in_sequence(self):
		floor, workstations = self.make_floor({"Sewing line 1": 3, "Cutting section": 2})
		lines = shop_floor.get_floor(floor)["lines"]

		self.assertEqual([line["name"] for line in lines], ["Cutting section", "Sewing line 1"])
		self.assertEqual([row.name for row in lines[1]["workstations"]], workstations["Sewing line 1"])

	def test_operator_sees_only_assigned_job_cards(self):
		workstation = make_jc_review_workstation()
		mine, other = make_jc_review_job_cards(workstation, 2)
		operator = make_jc_review_employee()
		shop_floor.assign_job_card(mine.name, [operator])

		self.assertEqual([row.name for row in shop_floor.get_my_job_cards(operator)], [mine.name])
		with self.set_user(create_user("shop-floor-operator@example.com", "Shop Floor User").name):
			station = shop_floor.get_station(workstation, operator)
			self.assertEqual(station["job_card"]["name"], mine.name)
			self.assertEqual(station["queue"], [])
			self.assertRaises(frappe.PermissionError, shop_floor.assign_job_card, other.name, [operator])
			self.assertRaises(frappe.ValidationError, shop_floor.start_job, other.name, [operator], operator)

	def test_busy_machine_hides_the_other_operators_job(self):
		workstation = make_jc_review_workstation()
		first, second = make_jc_review_job_cards(workstation, 2)
		owner, other = make_jc_review_employee(), make_jc_review_employee()
		shop_floor.assign_job_card(first.name, [owner])
		shop_floor.assign_job_card(second.name, [other])
		shop_floor.start_job(first.name, [owner], owner)

		with self.set_user(create_user("shop-floor-operator@example.com", "Shop Floor User").name):
			station = shop_floor.get_station(workstation, other)
		self.assertTrue(station["busy"])
		self.assertEqual(station["job_card"]["name"], second.name)
		self.assertEqual(station["activity"], [])

	def test_bundle_is_logged_and_completed(self):
		job_card = make_jc_review_job_cards(make_jc_review_workstation(), 1)[0]
		operator = make_jc_review_employee()
		shop_floor.assign_job_card(job_card.name, [operator])
		shop_floor.start_job(job_card.name, [operator], operator)

		shop_floor.log_progress(job_card.name, operator, completed_qty=9)
		self.assertRaises(frappe.ValidationError, shop_floor.complete_job, job_card.name, operator)
		shop_floor.log_progress(job_card.name, operator, process_loss_qty=1, loss_reason="Broken stitch")
		shop_floor.complete_job(job_card.name, operator)

		job_card.reload()
		self.assertEqual(
			(job_card.docstatus, job_card.total_completed_qty, job_card.process_loss_qty), (1, 9, 1)
		)

	def test_breakdown_pauses_the_job_and_restart_logs_downtime(self):
		workstation = make_jc_review_workstation()
		job_card = make_jc_review_job_cards(workstation, 1)[0]
		operator = make_jc_review_employee()
		job_card.start_timer(start_time=add_to_date(now(), minutes=-30), employees=operator)

		shop_floor.report_breakdown(workstation)
		job_card.reload()
		self.assertEqual((job_card.is_paused, job_card.time_logs[-1].pause_reason), (1, "Breakdown"))
		self.assertEqual(frappe.db.get_value("Workstation", workstation, "status"), "Problem")
		self.assertRaises(frappe.ValidationError, shop_floor.resume_job, job_card.name)

		downtime = shop_floor.restart_machine(workstation, "Machine malfunction", operator, "Belt replaced")
		job_card.reload()
		self.assertEqual(
			frappe.db.get_value("Downtime Entry", downtime, "stop_reason"), "Machine malfunction"
		)
		self.assertEqual(job_card.is_paused, 0)
		self.assertEqual([log.employee for log in job_card.time_logs if not log.to_time], [operator])
		self.assertNotEqual(frappe.db.get_value("Workstation", workstation, "status"), "Problem")

	def test_breakdown_needs_a_running_machine(self):
		self.assertRaises(frappe.ValidationError, shop_floor.report_breakdown, make_jc_review_workstation())

	def test_user_restricted_to_an_employee_cannot_act_as_anyone_else(self):
		job_card = make_jc_review_job_cards(make_jc_review_workstation(), 1)[0]
		operator, other = make_jc_review_employee(), make_jc_review_employee()
		shop_floor.assign_job_card(job_card.name, [operator])
		user = create_user("shop-floor-restricted@example.com", "Shop Floor User")
		add_user_permission("Employee", operator, user.name)

		with self.set_user(user.name):
			context = shop_floor.get_context()
			self.assertEqual((context["employee"].name, context["can_switch_operator"]), (operator, False))
			self.assertEqual([row.name for row in shop_floor.get_employees()], [operator])
			self.assertRaises(frappe.PermissionError, shop_floor.get_my_job_cards, other)
			self.assertRaises(
				frappe.PermissionError, shop_floor.start_job, job_card.name, [operator, other], operator
			)
			shop_floor.start_job(job_card.name, [operator], operator)

		manager = create_user("shop-floor-supervisor@example.com", "Shop Floor Manager")
		add_user_permission("Employee", operator, manager.name)
		with self.set_user(manager.name):
			self.assertTrue(shop_floor.get_context()["can_switch_operator"])
			self.assertIn(other, [row.name for row in shop_floor.get_employees()])
