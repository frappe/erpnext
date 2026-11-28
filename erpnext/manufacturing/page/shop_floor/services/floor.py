from collections import defaultdict

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, getdate

from erpnext.manufacturing.page.plant_builder.plant_builder import get_machine_shapes
from erpnext.manufacturing.page.shop_floor.services.job_cards import (
	JOB_CARD_FIELDS,
	add_people,
	get_allowed_employees,
	get_assigned_job_card_names,
	get_open_job_cards,
	is_manager,
)

WORKSTATION_FIELDS = [
	"name",
	"workstation_name",
	"workstation_type",
	"status",
	"production_line",
	"line_sequence",
	"warehouse",
	"production_capacity",
]


def get_context():
	allowed = get_allowed_employees()
	filters = {"name": allowed[0]} if allowed and len(allowed) == 1 else {"user_id": frappe.session.user}
	employee = frappe.db.get_value(
		"Employee", {**filters, "status": "Active"}, ["name", "employee_name", "image"], as_dict=True
	)
	return {
		"employee": employee,
		"allowed_employees": allowed,
		"can_switch_operator": not allowed or len(allowed) > 1,
		"is_manager": is_manager(),
		"plant_floors": frappe.get_all("Plant Floor", fields=["name", "company"], order_by="name"),
	}


def get_floor(plant_floor):
	workstations = get_workstations(plant_floor)
	names = [row.name for row in workstations]
	job_cards = get_open_job_cards({"workstation": ("in", names)}) if names else []
	by_workstation = defaultdict(list)
	for job_card in job_cards:
		by_workstation[job_card.workstation].append(job_card)

	for workstation in workstations:
		cards = by_workstation[workstation.name]
		workstation.current = next((row for row in cards if row.phase in ("running", "paused")), None)
		workstation.queue_count = len([row for row in cards if row is not workstation.current])

	return {"plant_floor": plant_floor, "lines": group_lines(workstations), "stats": get_stats(workstations)}


def get_workstations(plant_floor):
	workstations = frappe.get_list(
		"Workstation",
		filters={"plant_floor": plant_floor, "disabled": 0},
		fields=WORKSTATION_FIELDS,
		order_by="line_sequence asc, name asc",
	)
	add_machine_models(workstations)
	return workstations


def add_machine_models(workstations):
	types = {row.workstation_type for row in workstations if row.workstation_type}
	models = (
		dict(
			frappe.get_all(
				"Workstation Type",
				filters={"name": ("in", list(types))},
				fields=["name", "machine_model"],
				as_list=True,
			)
		)
		if types
		else {}
	)
	for row in workstations:
		row.machine_model = models.get(row.workstation_type) or "Machine"
		row.shapes = get_machine_shapes(frappe._dict(row))


def group_lines(workstations):
	lines = defaultdict(list)
	for row in workstations:
		lines[row.production_line or ""].append(row)

	named = sorted(name for name in lines if name)
	ordered = [{"name": name, "workstations": lines[name]} for name in named]
	if lines.get(""):
		ordered.append({"name": "", "workstations": lines[""]})
	return ordered


def get_stats(workstations):
	names = [row.name for row in workstations]

	def count(statuses):
		return len([row for row in workstations if row.status in statuses])

	return {
		"running": count({"Production"}),
		"idle": count({"Idle", "Off", "Setup"}),
		"down": count({"Problem"}),
		"maintenance": count({"Maintenance"}),
		"downtime_minutes": get_downtime_minutes(names),
		"completed": get_completed_count(names),
	}


def get_downtime_minutes(workstations):
	if not workstations:
		return 0

	downtime = frappe.qb.DocType("Downtime Entry")
	minutes = (
		frappe.qb.from_(downtime)
		.select(Sum(downtime.downtime))
		.where(
			(downtime.workstation.isin(workstations))
			& (downtime.from_time >= getdate())
			& (downtime.docstatus < 2)
		)
	).run()
	return round(minutes[0][0] or 0) if minutes else 0


def get_completed_count(workstations):
	if not workstations:
		return 0

	return frappe.db.count(
		"Job Card",
		{
			"workstation": ("in", workstations),
			"docstatus": 1,
			"actual_end_date": ("between", [getdate(), add_days(getdate(), 1)]),
		},
	)


def get_employees(plant_floor=None, search=None):
	filters = {"status": "Active"}
	if (allowed := get_allowed_employees()) is not None:
		filters["name"] = ("in", allowed)
	if plant_floor:
		filters["company"] = frappe.get_cached_value("Plant Floor", plant_floor, "company")

	or_filters = (
		{"name": ("like", f"%{search}%"), "employee_name": ("like", f"%{search}%")} if search else None
	)
	employees = frappe.get_all(
		"Employee",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "employee_name", "image", "designation"],
		order_by="employee_name asc",
		limit=200,
	)
	add_assignments(employees)
	return sorted(employees, key=lambda row: not row.job_cards)


def add_assignments(employees):
	names = [row.name for row in employees]
	if not names:
		return

	rows = frappe.get_all(
		"Job Card Time Log",
		filters={"parenttype": "Job Card", "employee": ("in", names), "parentfield": "employee"},
		fields=["employee", "parent"],
	)
	open_cards = (
		{row.name: row for row in get_open_job_cards({"name": ("in", list({row.parent for row in rows}))})}
		if rows
		else {}
	)
	by_employee = defaultdict(list)
	for row in rows:
		if card := open_cards.get(row.parent):
			by_employee[row.employee].append(card)

	for employee in employees:
		cards = by_employee[employee.name]
		employee.job_cards = [
			{"name": card.name, "operation": card.operation, "workstation": card.workstation}
			for card in cards
		]
		employee.working_on = next((card.workstation for card in cards if employee.name in card.crew), None)


def get_my_job_cards(employee):
	names = get_assigned_job_card_names(employee)
	job_cards = get_open_job_cards({"name": ("in", names)}) if names else []
	floors = (
		dict(
			frappe.get_all(
				"Workstation",
				filters={"name": ("in", list({row.workstation for row in job_cards}))},
				fields=["name", "plant_floor"],
				as_list=True,
			)
		)
		if job_cards
		else {}
	)
	for row in job_cards:
		row.plant_floor = floors.get(row.workstation)
	return job_cards


def get_job_card_list(plant_floor, show="open", operation=None):
	workstations = frappe.get_list("Workstation", filters={"plant_floor": plant_floor}, pluck="name")
	if not workstations:
		return []

	filters = {"workstation": ("in", workstations)}
	if operation:
		filters["operation"] = operation
	if show == "completed":
		return get_completed_job_cards(filters)

	job_cards = get_open_job_cards(filters)
	if show == "unassigned":
		return [row for row in job_cards if not row.assigned]
	return job_cards


def get_completed_job_cards(filters):
	job_cards = frappe.get_list(
		"Job Card",
		filters={"docstatus": 1, "actual_end_date": (">=", add_days(getdate(), -7)), **filters},
		fields=JOB_CARD_FIELDS,
		order_by="actual_end_date desc",
		limit=200,
	)
	add_people(job_cards)
	return job_cards
