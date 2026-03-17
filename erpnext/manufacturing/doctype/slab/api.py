from datetime import date

from frappe import frappe
from frappe import utils as frappe_utils
from frappe.exceptions import ValidationError
from frappe.query_builder.functions import Count

from erpnext.accounts.doctype.fiscal_year.fiscal_year import FiscalYear
from erpnext.manufacturing.doctype.slab.slab import ALLOWED_STAGES, Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.setup.doctype.mahi_granites_settings.mahi_granites_settings import MahiGranitesSettings


@frappe.whitelist()
def create_slab(line: str, child_line: str, type: str, job_card_number: str | None = None):
	new_slab: Slab = frappe.new_doc("Slab")  # pyright: ignore[reportAssignmentType]
	new_slab.line = line
	new_slab.child_line = child_line
	new_slab.template = type
	new_slab.current_job_card = job_card_number
	new_slab.batch_number = _generate_batch_number(line)

	slab_number: int = _get_slab_number(new_slab.batch_number, line)
	new_slab.number = slab_number
	new_slab.serial_number = f"{slab_number:04d}"

	new_slab.created_on = frappe_utils.now_datetime()
	current_stage = ALLOWED_STAGES[0]
	new_slab.status = current_stage  # pyright: ignore[reportAttributeAccessIssue]

	# Create the first line item for the slab history as distribution.
	slab_history: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
	slab_history.idx = 1
	slab_history.station = current_stage
	slab_history.in_time = frappe_utils.now_datetime()
	slab_history.job_card_number = job_card_number
	new_slab.slab_history.append(slab_history)

	new_slab.save(ignore_permissions=True)
	return new_slab


@frappe.whitelist()
def checkout_slab(slab_number: str):
	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]

	# Get the last item in slab history
	last_history = slab.slab_history[-1]

	# Check if the out time on the last history item is None
	if last_history.out_time is not None:
		frappe.throw("Slab is already checked out of the current station.")

	last_history.out_time = frappe_utils.now_datetime()
	total_seconds = (last_history.out_time - last_history.in_time).total_seconds()  # pyright: ignore[reportOperatorIssue]
	last_history.total_time_in_minutes = total_seconds / 60

	if slab.status == "Quarantine":
		# Get Mahi Granites Settings to check if the slab is quarantined prematurely.
		settings: MahiGranitesSettings = frappe.get_single("Mahi Granites Settings")  # pyright: ignore[reportAssignmentType]
		if settings.min_quarantine_hours > total_seconds / 3600:
			slab.is_prematurely_unquarantined = True

	slab.is_cur_stage_complete = True

	slab.save(ignore_permissions=True)

	frappe.publish_realtime("slab_checkout", slab)


@frappe.whitelist()
def re_press_slab(slab_number: str):
	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]
	if slab.status != "Pressing":
		frappe.throw("Cannot re-press a slab that is not in the pressing stage")

	# Get the last item in slab history
	last_history = slab.slab_history[-1]
	# Check if the out time on the last history item is None. If it is, checkout the slab first.
	if last_history.out_time is None:
		checkout_slab(slab_number)

	slab.reload()
	slab.is_repressed = True
	slab.save(ignore_permissions=True)

	move_slab_to(slab_number, "Re-Pressing", slab.current_job_card)


@frappe.whitelist()
def move_slab_to(
	slab_number: str,
	next_stage: str,
	job_card_number: str | None = None,
	checkout_and_move=False,
):
	checkout_and_move = bool(checkout_and_move)
	# Validation: Check if the given stage is valid.
	allowed_stages_lower = [stage.lower() for stage in ALLOWED_STAGES]
	if next_stage.lower() not in allowed_stages_lower:
		frappe.throw("Invalid next stage")

	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]

	current_stage_index = allowed_stages_lower.index(slab.status.lower())
	next_stage_index = allowed_stages_lower.index(next_stage.lower())
	next_stage = ALLOWED_STAGES[next_stage_index]

	# Validation: Check the direction of transition
	if next_stage_index < current_stage_index or (
		next_stage_index == current_stage_index and next_stage.lower() != "Re-pressing"
	):
		frappe.throw(f"Invalid stage transition: cannot move from {slab.status} to {next_stage}")

	# If the slab is not checked out yet, check it out of the previous
	# stage before moving it to the next stage, based on the flag set.
	last_history = slab.slab_history[-1]
	if last_history.out_time is None:
		if not checkout_and_move:
			frappe.throw("Cannot move slab without checking out")

		# checkout_slab(slab_number)
		slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]

	slab.status = next_stage  # pyright: ignore[reportAttributeAccessIssue]
	slab.is_cur_stage_complete = False
	slab.current_job_card = job_card_number or slab.current_job_card
	slab.status = ALLOWED_STAGES[next_stage_index]  # pyright: ignore[reportAttributeAccessIssue]
	# if next_stage.lower() != "trimming":
	# 	next_job_card_info = find_next_job_card(job_card_number or slab.slab_history[-1].job_card_number)
	# 	slab.current_job_card = next_job_card_info["next_job_card"]

	# Append the next stage to the slab history.
	slab_history: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
	slab_history.idx = len(slab.slab_history) + 1
	slab_history.station = ALLOWED_STAGES[next_stage_index]
	slab_history.in_time = frappe_utils.now_datetime()
	slab_history.job_card_number = job_card_number
	slab.slab_history.append(slab_history)

	slab.save(ignore_permissions=True)
	frappe.publish_realtime("slab_move", slab)


@frappe.whitelist()
def get_slabs_in(line: str, current_stage: str) -> list[dict]:
	slabs = frappe.db.get_list(
		"Slab",
		ignore_permissions=True,
		filters={
			"line": line,
			"status": current_stage,
			"is_cur_stage_complete": False,
		},
		fields=[
			"name",
			"number",
			"serial_number",
			"status",
			"line",
			"batch_number",
			"template",
			"is_cur_stage_complete",
			"creation",
			"modified",
			"current_job_card",
		],
	)
	return slabs


@frappe.whitelist()
def get_slabs_for(line: str, next_stage: str, limit=1, include_current_stage=False) -> list[dict]:
	include_current_stage = bool(include_current_stage)
	# Determine valid previous stages based on the next_stage and rules
	valid_previous_stages = []

	# Check if next_stage is valid
	next_stage = next_stage.title()
	if next_stage in ALLOWED_STAGES:
		target_index = ALLOWED_STAGES.index(next_stage)

		# Special handling for Heating (Pressing -> Heating, Re-Pressing -> Heating)
		if next_stage == "Heating":
			valid_previous_stages = ["Pressing", "Re-Pressing"]
		# Special handling for Re-pressing (Pressing does NOT lead to Re-Pressing here)
		elif next_stage == "Re-Pressing":
			valid_previous_stages = []
		# General case: previous index in ALLOWED_STAGES
		elif target_index > 0:
			valid_previous_stages = [ALLOWED_STAGES[target_index - 1]]

	if not valid_previous_stages:
		return []

	if include_current_stage:
		valid_previous_stages.append(next_stage)

	slabs = frappe.db.get_list(
		"Slab",
		order_by="modified asc",
		ignore_permissions=True,
		filters={"status": ["in", valid_previous_stages], "is_cur_stage_complete": 1, "line": line},
		limit=limit, # Limit one to send only the first slab
		fields=[
			"name",
			"serial_number",
			"status",
			"line",
			"batch_number",
			"template",
			"creation",
			"modified",
			"current_job_card",
		],
	)

	return slabs


@frappe.whitelist()
def get_batch_numbers(include_child_lines = False):
	production_lines = frappe.db.get_list(
		"Production Line",
		ignore_permissions=True,
		fields=["name", "parent_line", "is_group"],
		filters={
			"is_active": 1,
		}
	)

	batch_numbers = {}

	for line in production_lines:
		if not line.is_group and not include_child_lines:
			continue

		batch_numbers[line.name] = _generate_batch_number(line.name)

	return batch_numbers


def _generate_batch_number(line: str):
	today = date.today()

	# A: Get the current fiscal year
	fiscal_years: list = frappe.db.get_all(
		"Fiscal Year", filters=[["year_start_date", "<=", today], ["year_end_date", ">=", today]], fields=["year_start_date", "year_end_date"]
	)  # pyright: ignore[reportAssignmentType]

	if not fiscal_years:
		frappe.throw("No fiscal year found for the current date.", ValidationError)

	fiscal_year: FiscalYear = fiscal_years[0]

	year_code = chr(65 + fiscal_year.year_start_date.year - 2017)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]

	# B: Get total days in the fiscal year until today
	time_diff = today - fiscal_year.year_start_date  # pyright: ignore[reportOperatorIssue, reportOptionalMemberAccess]
	total_days_so_far = time_diff.days

	# C: Get the total holidays from the first day of the fiscal year of the year till today
	year_start_date = (
		fiscal_year.year_start_date.strftime("%Y-%m-%d")  # pyright: ignore[reportAttributeAccessIssue]
		if fiscal_year and fiscal_year.year_start_date
		else None
	)

	year_end_date = (
		fiscal_year.year_end_date.strftime("%Y-%m-%d") if fiscal_year and fiscal_year.year_end_date else None  # pyright: ignore[reportAttributeAccessIssue]
	)

	today_string = today.strftime("%Y-%m-%d")
	HOLIDAY_LIST = frappe.qb.DocType("Holiday List")

	query_conditions = (
		(HOLIDAY_LIST.from_date <= year_start_date) & (HOLIDAY_LIST.to_date >= year_start_date)
	) | ((HOLIDAY_LIST.from_date <= year_end_date) & (HOLIDAY_LIST.to_date >= year_end_date))

	query = frappe.qb.from_(HOLIDAY_LIST).select(Count("*")).where(query_conditions)

	result = query.run()
	holiday_list_count = result[0][0]

	if holiday_list_count == 0:
		frappe.throw("No holidays found. Please create a holiday list for the current year.", ValidationError)

	# format date as string
	holidays = frappe.db.get_list(
		"Holiday",
		filters=[["holiday_date", "between", [year_start_date, today_string]]],
		fields=["holiday_date"],
		ignore_permissions=True,
	)

	if today_string in [holiday["holiday_date"].strftime("%Y-%m-%d") for holiday in holidays]:
		frappe.throw("Today is a holiday. Cannot generate batch number.", ValidationError)

	holiday_count = len(holidays)

	# Calculate A - B
	total_working_days = total_days_so_far - holiday_count

	return f"{line}{year_code}/{total_working_days:03d}"


def _get_slab_number(batch: str, line: str) -> int:
	today = date.today()
	curr_month = today.month
	curr_year = today.year

	month_start = f"{curr_year}-{curr_month:02d}-01"

	batch_prefix = batch.split("/")[0]

	mahi_granites_settings: MahiGranitesSettings = frappe.get_doc("Mahi Granites Settings")  # pyright: ignore[reportAssignmentType]
	slab_seed = next((seed.seed for seed in mahi_granites_settings.slab_seeds if seed.line == line and seed.seed_month and seed.seed_month.strftime("%Y-%m-%d") == month_start), 0)  # pyright: ignore

	slab_count: int = (
		frappe.db.count(
			"Slab",
			filters=[
				["batch_number", "like", f"{batch_prefix}%"],
				["creation", ">=", month_start],
			],
		)
		+ slab_seed
	)

	return slab_count or 0
