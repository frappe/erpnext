from datetime import date

from frappe import frappe
from frappe.query_builder.functions import Count

from erpnext.manufacturing.doctype.slab.slab import ALLOWED_STAGES, Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.setup.doctype.mahi_granites_settings.mahi_granites_settings import MahiGranitesSettings


@frappe.whitelist()
def create_slab(line: str, type: str, job_card_number: str | None = None):
	new_slab: Slab = frappe.new_doc("Slab")  # pyright: ignore[reportAssignmentType]
	new_slab.line = line
	new_slab.template = type
	new_slab.current_job_card = job_card_number
	new_slab.batch_number = _generate_batch_number(line)

	slab_number: int = _get_slab_number()
	new_slab.number = slab_number
	new_slab.serial_number = f"{slab_number:04d}"

	new_slab.created_on = frappe.utils.now_datetime()
	current_stage = ALLOWED_STAGES[0]
	new_slab.status = current_stage  # pyright: ignore[reportAttributeAccessIssue]

	# Create the first line item for the slab history as distribution.
	slab_history: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
	slab_history.idx = 1
	slab_history.station = current_stage
	slab_history.in_time = frappe.utils.now_datetime()
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

	last_history.out_time = frappe.utils.now_datetime()
	last_history.total_time_in_minutes = (last_history.out_time - last_history.in_time).total_seconds() / 60  # pyright: ignore[reportOperatorIssue]

	if slab.status == "Quarantine":
		# Get Mahi Granites Settings to check if the slab is quarantined prematurely.
		settings: MahiGranitesSettings = frappe.get_single("Mahi Granites Settings")
		if (
			settings.min_quarantine_hours
			> (last_history.out_time - last_history.in_time).total_seconds() / 3600
		):
			slab.is_prematurely_unquarantined = True

	slab.is_cur_stage_complete = True

	slab.save(ignore_permissions=True)

	frappe.publish_realtime("slab_checkout", slab)


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

	slab = frappe.get_doc("Slab", slab_number)

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
		slab: Slab = frappe.get_doc("Slab", slab_number)

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
	slab_history.in_time = frappe.utils.now_datetime()
	slab_history.job_card_number = job_card_number
	slab.slab_history.append(slab_history)

	slab.save(ignore_permissions=True)
	frappe.publish_realtime("slab_move", slab)


@frappe.whitelist()
def get_slabs_in(line: str, current_stage: str) -> list[dict]:
	slabs = frappe.db.get_list(
		"Slab",
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

		# Special handling for Heating (Pressing -> Heating, Re-pressing -> Heating)
		if next_stage == "Heating":
			valid_previous_stages = ["Pressing", "Re-pressing"]
		# Special handling for Re-pressing (Pressing does NOT lead to Re-pressing here)
		elif next_stage == "Re-pressing":
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


def _generate_batch_number(line: str):
	today = date.today()
	year_code = chr(65 + today.year - 2017)

	# A: Get total days in the year until today
	total_days_so_far = today.timetuple().tm_yday

	# B: Get the total holidays from the first day of the year till today
	year_start = f"{today.year}-01-01"
	today_string = today.strftime("%Y-%m-%d")
	HOLIDAY_LIST = frappe.qb.DocType("Holiday List")
	query = (
		frappe.qb.from_(HOLIDAY_LIST)
		.select(Count("*"))
		.where(HOLIDAY_LIST.from_date <= today_string)
		.where(HOLIDAY_LIST.to_date >= today_string)
	)

	result = query.run()
	holiday_list_count = result[0][0]

	if holiday_list_count == 0:
		frappe.throw("No holidays found. Please create a holiday list for the current year.")

	# format date as string
	holidays = frappe.db.count(
		"Holiday",
		filters=[["holiday_date", "between", [year_start, today.strftime("%Y-%m-%d")]]],
	)

	# Calculate A - B
	total_working_days = total_days_so_far - holidays

	return f"{line}{year_code}/{total_working_days:03d}"


def _get_slab_number():
	today = date.today()
	curr_month = today.month
	curr_year = today.year

	month_start = f"{curr_year}-{curr_month:02d}-01"

	slab_count = frappe.db.count("Slab", filters={"created_on": [">=", month_start]}) + 20
	return slab_count
