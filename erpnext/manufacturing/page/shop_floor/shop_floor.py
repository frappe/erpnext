import frappe

from erpnext.manufacturing.page.shop_floor.services import actions, floor, quality, station
from erpnext.manufacturing.page.shop_floor.services.job_cards import validate_employees

PAGE_ROLES = {
	"Shop Floor User",
	"Shop Floor Manager",
	"Manufacturing User",
	"Manufacturing Manager",
	"System Manager",
}


def check_access(*employees):
	frappe.only_for(list(PAGE_ROLES))
	validate_employees(
		[name for group in employees for name in (group if isinstance(group, list) else [group])]
	)


def parse_list(value):
	return frappe.parse_json(value) if isinstance(value, str) else value


@frappe.whitelist()
def get_context() -> dict:
	check_access()
	return floor.get_context()


@frappe.whitelist()
def get_floor(plant_floor: str) -> dict:
	check_access()
	return floor.get_floor(plant_floor)


@frappe.whitelist()
def get_employees(plant_floor: str | None = None, search: str | None = None) -> list:
	check_access()
	return floor.get_employees(plant_floor, search)


@frappe.whitelist()
def get_my_job_cards(employee: str) -> list:
	check_access(employee)
	return floor.get_my_job_cards(employee)


@frappe.whitelist()
def get_job_cards(plant_floor: str, show: str = "open", operation: str | None = None) -> list:
	check_access()
	return floor.get_job_card_list(plant_floor, show, operation)


@frappe.whitelist()
def get_station(workstation: str, employee: str | None = None) -> dict:
	check_access(employee)
	return station.get_station(workstation, employee)


@frappe.whitelist(methods=["POST"])
def start_job(job_card: str, employees: list | str, employee: str | None = None) -> None:
	employees = parse_list(employees)
	check_access(employee, employees)
	actions.start_job(job_card, employees, employee)


@frappe.whitelist(methods=["POST"])
def pause_job(job_card: str, reason: str, employee: str | None = None) -> None:
	check_access(employee)
	actions.get_job_card(job_card, employee).pause_job(end_time=frappe.utils.now_datetime(), reason=reason)


@frappe.whitelist(methods=["POST"])
def resume_job(job_card: str, employee: str | None = None) -> None:
	check_access(employee)
	actions.resume_job(job_card, employee)


@frappe.whitelist(methods=["POST"])
def change_crew(job_card: str, employees: list | str, employee: str | None = None) -> None:
	employees = parse_list(employees)
	check_access(employee, employees)
	actions.get_job_card(job_card, employee).change_crew(employees)


@frappe.whitelist(methods=["POST"])
def log_progress(
	job_card: str,
	employee: str,
	completed_qty: float = 0,
	process_loss_qty: float = 0,
	loss_reason: str | None = None,
) -> None:
	check_access(employee)
	doc = actions.get_job_card(job_card, employee)
	doc.log_progress(employee, completed_qty, process_loss_qty, loss_reason)


@frappe.whitelist(methods=["POST"])
def complete_job(job_card: str, employee: str | None = None) -> None:
	check_access(employee)
	actions.complete_job(job_card, employee)


@frappe.whitelist(methods=["POST"])
def assign_job_card(job_card: str, employees: list | str) -> list:
	check_access()
	return actions.assign_job_card(job_card, parse_list(employees))


@frappe.whitelist(methods=["POST"])
def report_breakdown(workstation: str) -> None:
	check_access()
	actions.report_breakdown(workstation)


@frappe.whitelist(methods=["POST"])
def restart_machine(workstation: str, stop_reason: str, operator: str, remarks: str | None = None) -> str:
	check_access(operator)
	return actions.restart_machine(workstation, stop_reason, operator, remarks)


@frappe.whitelist()
def get_quality_inspection_checklist(job_card: str) -> dict:
	check_access()
	return quality.get_quality_inspection_checklist(job_card)


@frappe.whitelist(methods=["POST"])
def submit_quality_inspection(job_card: str, readings: str | None = None) -> dict:
	check_access()
	return quality.submit_quality_inspection(job_card, readings)
