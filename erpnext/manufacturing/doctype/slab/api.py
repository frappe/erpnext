from datetime import date, datetime, timedelta

from frappe import frappe
from frappe import utils as frappe_utils
from frappe.exceptions import ValidationError
from frappe.query_builder.functions import Count

from erpnext.accounts.doctype.fiscal_year.fiscal_year import FiscalYear
from erpnext.manufacturing.doctype.oven_operation.oven_operation import OvenOperation
from erpnext.manufacturing.doctype.preliminary_quality_check.preliminary_quality_check import (
	PreliminaryQualityCheck,
)
from erpnext.manufacturing.doctype.slab.slab import ALLOWED_STAGES, Slab
from erpnext.manufacturing.doctype.slab_batch_number.api import delete_batch_numbers_older_than
from erpnext.manufacturing.doctype.slab_batch_number.slab_batch_number import SlabBatchNumber
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.manufacturing.doctype.slab_quality_report.api import create_slab_quality_report
from erpnext.manufacturing.doctype.slab_quality_report.slab_quality_report import SlabQualityReport
from erpnext.setup.doctype.attendance_shift.attendance_shift import AttendanceShift
from erpnext.setup.doctype.mahi_granites_settings.mahi_granites_settings import MahiGranitesSettings

STAGES_TO_SKIP_IN_AUTO_MOVE = ["Re-Pressing", "Packed", "Shipped", "Discarded", "Quality Check"]


@frappe.whitelist()
def create_slab(
	line: str,
	child_line: str,
	type: str,
	job_card_number: str | None = None,
	slab_history: list[SlabHistory] | None = None,
):
	new_slab: Slab = frappe.new_doc("Slab")  # pyright: ignore[reportAssignmentType]
	new_slab.line = line
	new_slab.child_line = child_line
	new_slab.template = type
	new_slab.current_job_card = job_card_number
	new_slab.batch_number = _generate_slab_batch(line, create_and_get=True)

	slab_number: int = _get_slab_number(new_slab.batch_number, line)
	new_slab.number = slab_number
	new_slab.serial_number = f"{slab_number:04d}"

	new_slab.created_on = frappe_utils.now_datetime()
	current_stage = ALLOWED_STAGES[0]
	new_slab.status = current_stage  # pyright: ignore[reportAttributeAccessIssue]

	if slab_history:
		new_slab.slab_history = slab_history

	# Create the first line item for the slab history as distribution.
	slab_history_item: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
	slab_history_item.idx = len(new_slab.slab_history) + 1
	slab_history_item.station = current_stage
	slab_history_item.in_time = frappe_utils.now_datetime()
	slab_history_item.job_card_number = job_card_number
	new_slab.slab_history.append(slab_history_item)

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

	if slab.status == "Curing":
		# Get Mahi Granites Settings to check if the slab is moved out of curing prematurely.
		settings: MahiGranitesSettings = frappe.get_single("Mahi Granites Settings")  # pyright: ignore[reportAssignmentType]
		if settings.min_curing_hours > total_seconds / 3600:
			slab.is_prematurely_checked_out = True

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
	slab.current_job_card = job_card_number
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
def get_slabs_for(line: str, next_stage: str, limit=1, include_current_stage=False) -> list[Slab]:
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
		limit=limit,  # Limit one to send only the first slab
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
def get_batch_numbers(include_child_lines=False):
	production_lines = frappe.db.get_list(
		"Production Line",
		ignore_permissions=True,
		fields=["name", "parent_line", "is_group"],
		filters={
			"is_active": 1,
		},
	)

	batch_numbers = {}

	for line in production_lines:
		if not line.is_group and not include_child_lines:
			continue

		batch_numbers[line.name] = _generate_slab_batch(line.name)

	return batch_numbers


@frappe.whitelist()
def get_valid_next_stages(current_stage: str) -> list[str]:
	allowed_stages = [stage.lower() for stage in ALLOWED_STAGES]
	try:
		current_stage_index = allowed_stages.index(current_stage.lower())
	except ValueError:
		return []

	valid_stages = []
	for idx, stage in enumerate(ALLOWED_STAGES):
		if stage in STAGES_TO_SKIP_IN_AUTO_MOVE or idx <= current_stage_index:
			continue

		valid_stages.append(stage)

	return valid_stages


@frappe.whitelist()
def move_slab_iteratively_to(slab_name: str, final_stage: str, obsevation: PreliminaryQualityCheck | OvenOperation | SlabQualityReport | None = None):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	# If the slab's current process is not complete, finish the process
	from erpnext.manufacturing.page.operator_station.operator_station import (
		finish_process,
		get_next_work_item,
		start_process,
	)

	obs_creation_func_map = {
		"curing": _create_preliminary_qc,
		"heating": _create_oven_operation_params,
		"quality check": _create_final_qc,
	}

	try:
		frappe.db.begin()

		# If the current stage of the slab is not complete yet, finish it before proceeding.
		if not slab.is_cur_stage_complete:
			# Add the default stage observations, if applicable
			func = obs_creation_func_map.get(slab.status.lower())
			if func:
				func(slab, obsevation)

			if slab.current_job_card:
				finish_process(
					slab.current_job_card, slab.status.lower(), transfer_materials=slab.status.lower() != "cooling", should_stop_machine=False
				)

			elif slab.status.lower() == "curing":
				_finish_curing(slab_name)

			else:
				checkout_slab(str(slab.name))

		next_stages = get_valid_next_stages(slab.status)
		for stage in next_stages:
			# Get the name of the top job card for the process
			top_job_card_name = (get_next_work_item(stage.lower(), slab.line).get('job_card', {}) or {}).get('name')

			if top_job_card_name:
				start_process(top_job_card_name, slab_name, slab.template, stage.lower())
				finish_process(top_job_card_name, stage.lower(), transfer_materials=stage.lower() != "cooling", should_stop_machine=False)
			else:
				move_slab_to(slab_name, stage)

				if stage.lower() == "curing":
					_finish_curing(slab_name)
				else:
					checkout_slab(slab_name)

			# Add the default stage observations, if applicable
			func = obs_creation_func_map.get(stage.lower())
			if func:
				func(slab_name, obsevation)

			if stage.lower() == final_stage:
				break

		frappe.db.commit()

	except Exception:
		frappe.db.rollback()


def _finish_curing(slab_name: str):
	from erpnext.manufacturing.page.slab_loading_station.slab_loading_station import finish_curing
	finish_curing(slab_name)


def pause_or_resume_slab_operation(slab_number: str, pause: bool):
	# Get the slab document
	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]
	# Get the last item in slab history
	last_history = slab.slab_history[-1]

	# Check if the out time on the last history item is None
	if pause and last_history.out_time is not None:
		frappe.throw("Invalid Operation: Slab operation is already paused.")

	if not pause and last_history.out_time is None:
		frappe.throw("Invalid Operation: Slab operation is not paused.")

	if pause:
		last_history.out_time = frappe_utils.now_datetime()
		total_seconds = (last_history.out_time - last_history.in_time).total_seconds()  # pyright: ignore[reportOperatorIssue]
		last_history.total_time_in_minutes = total_seconds / 60
		slab.is_paused = True
	else:
		slab_history: SlabHistory = frappe.new_doc("Slab History")  # pyright: ignore[reportAssignmentType]
		slab_history.idx = last_history.idx + 1
		slab_history.station = last_history.station
		slab_history.in_time = frappe_utils.now_datetime()
		slab_history.job_card_number = last_history.job_card_number
		slab.slab_history.append(slab_history)
		slab.is_paused = False

	slab.save(ignore_permissions=True)


def _generate_slab_batch(line: str, create_and_get: bool = False):
	today = date.today()

	# A: Get the current fiscal year
	fiscal_years: list = frappe.db.get_all(
		"Fiscal Year",
		filters=[["year_start_date", "<=", today], ["year_end_date", ">=", today]],
		fields=["year_start_date", "year_end_date"],
	)  # pyright: ignore[reportAssignmentType]

	if not fiscal_years:
		frappe.throw("No fiscal year found for the current date.", ValidationError)

	fiscal_year: FiscalYear = fiscal_years[0]

	year_code = chr(65 + fiscal_year.year_start_date.year - 2017)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]

	batch_number = _get_batch_number_from_list(today, fiscal_year, create_and_get)

	return f"{line}{year_code}/{batch_number}"


def _calculate_batch_number_based_on_working_days(today: date, fiscal_year: FiscalYear):
	# B: Get total days in the fiscal year until today
	time_diff = today - fiscal_year.year_start_date  # pyright: ignore[reportOperatorIssue, reportOptionalMemberAccess]
	total_days_so_far = time_diff.days

	attendance_shifts = frappe.db.get_all(
		"Attendance Shift",
		fields=["name", "start_time", "end_time", "does_span_next_day"],
		limit=1,
		order_by="start_time DESC",
	)

	last_shift = attendance_shifts[0] if attendance_shifts else None
	if not last_shift:
		raise frappe.ValidationError("No attendance shifts found.")

	shift = last_shift
	now_time = datetime.now()
	shift_start_hour = shift.start_time.seconds / 3600
	start_day_factor = 1 if shift.does_span_next_day and now_time.hour < shift_start_hour else 0
	shift_start_datetime = (
		datetime(today.year, today.month, today.day) - timedelta(days=start_day_factor) + shift.start_time
	)
	shift_end_datetime = datetime(today.year, today.month, today.day) + shift.end_time

	# If the current time falls in the LAST shift of the day AND is after midnight, subtract 1 from total_days_so_far so that the batch number still reflects that of the previous day.
	if shift_start_datetime <= now_time <= shift_end_datetime:
		total_days_so_far -= 1

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
	total_working_days = total_days_so_far - holiday_count + 1
	return f"{total_working_days:03d}"


def _get_batch_number_from_list(today: date, fiscal_year: FiscalYear, create_and_get: bool = False) -> str:

	attendance_shifts: list[AttendanceShift] = frappe.db.get_all(
		"Attendance Shift",
		fields=["name", "start_time", "end_time", "does_span_next_day"],
		limit=1,
		order_by="start_time DESC",
	)

	last_shift = attendance_shifts[0] if attendance_shifts else None
	if not last_shift:
		raise frappe.ValidationError("No attendance shifts found.")

	now_time = datetime.now()
	shift_end_hour = last_shift.end_time.seconds / 3600  # pyright: ignore[reportAttributeAccessIssue]
	start_day_factor = 1 if last_shift.does_span_next_day and now_time.hour < shift_end_hour else 0
	today -= timedelta(days=start_day_factor)

	# Get today's batch number.
	slab_batch_number: str = frappe.db.get_value(  # pyright: ignore[reportAssignmentType]
		"Slab Batch Number",
		filters={"date": today.strftime("%Y-%m-%d")},
		fieldname="name",
	)

	fy_start_date: datetime = fiscal_year.year_start_date  # pyright: ignore[reportAssignmentType]
	# A buffer date to account for holidays and other non-working days at the start of the fiscal year
	buffer_date: datetime = fy_start_date + timedelta(days=10)  # pyright: ignore[reportAssignmentType]

	if slab_batch_number:
		return slab_batch_number.split("-")[-1]

	# If `create_and_get` is True, create a new batch number if one does not exist for today.
	elif create_and_get:
		if (
			fy_start_date.year == today.year
			and fy_start_date.month == today.month
			and fy_start_date.day <= today.day
			and today.day <= buffer_date.day
		):  # pyright: ignore[reportAttributeAccessIssue]
			delete_batch_numbers_older_than(fy_start_date.strftime("%Y-%m-%d"))

		slab_batch: SlabBatchNumber = frappe.new_doc("Slab Batch Number")  # pyright: ignore[reportAssignmentType]
		slab_batch.date = today.strftime("%Y-%m-%d")
		slab_batch.save(ignore_permissions=True)
		return str(slab_batch.name).split("-")[-1]

	# Else, throw an exception if one does not exist.
	frappe.throw("No batch number found for today.", ValidationError)
	return ""


def _get_slab_number(batch: str, line: str) -> int:
	today = date.today()
	curr_month = today.month
	curr_year = today.year

	month_start = f"{curr_year}-{curr_month:02d}-01"

	batch_prefix = batch.split("/")[0]

	mahi_granites_settings: MahiGranitesSettings = frappe.get_doc("Mahi Granites Settings")  # pyright: ignore[reportAssignmentType]
	slab_seed = next(
		(
			seed.seed
			for seed in mahi_granites_settings.slab_seeds
			if seed.line == line and seed.seed_month and seed.seed_month.strftime("%Y-%m-%d") == month_start  # pyright: ignore[reportAttributeAccessIssue]
		),
		0,
	)  # pyright: ignore

	slab_count: int = (
		frappe.db.count(
			"Slab",
			filters=[
				["batch_number", "like", f"{batch_prefix}%"],
				["creation", ">=", month_start],
			],
		)
		+ slab_seed
	) + 1

	return slab_count or 0


def _create_preliminary_qc(slab_name: str, preliminary_qc: PreliminaryQualityCheck | None = None):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	curing_history_item = next((item for item in slab.slab_history if item.station == "Curing"), None)
	if curing_history_item and not preliminary_qc and curing_history_item.preliminary_qc:
		preliminary_qc = frappe.get_doc("Preliminary Quality Check", str(curing_history_item.preliminary_qc))  # pyright: ignore[reportAssignmentType]

	if not preliminary_qc:
		preliminary_qc = frappe.new_doc("Preliminary Quality Check")  # pyright: ignore[reportAssignmentType]
		if not preliminary_qc:
			raise Exception("Preliminary Quality Check could not be created.")

	preliminary_qc.slab = preliminary_qc.slab or str(slab.name)
	preliminary_qc.slab_template = preliminary_qc.slab_template or slab.template
	preliminary_qc.h_bend = preliminary_qc.h_bend or 0
	preliminary_qc.v_bend = preliminary_qc.v_bend or 0
	preliminary_qc.d1_bend = preliminary_qc.d1_bend or 0
	preliminary_qc.d2_bend = preliminary_qc.d2_bend or 0

	from erpnext.manufacturing.doctype.preliminary_quality_check.api import create_preliminary_quality_check
	create_preliminary_quality_check(str(slab.name), preliminary_qc)


def _create_oven_operation_params(slab_name: str, oven_params: OvenOperation | None = None):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	heating_slab_history_item = next((h for h in slab.slab_history if h.station == "Heating"), None)
	if heating_slab_history_item and not oven_params and heating_slab_history_item.oven_params:
		oven_params = frappe.get_doc("Oven Operation", str(heating_slab_history_item.oven_params))  # pyright: ignore[reportAssignmentType]

	if not oven_params:
		oven_params = frappe.new_doc("Oven Operation") # pyright: ignore[reportAssignmentType]
		if not oven_params:
			raise Exception("Oven Operation could not be created.")

	oven_params.slab = oven_params.slab or str(slab.name)
	oven_params.slab_color = oven_params.slab_color or slab.template
	oven_params.job_card = oven_params.job_card or str(slab.last_active_job_card)

	oven_name = frappe.get_value("Oven", {"line": slab.line}, "name")
	oven_racks = frappe.get_list("Oven Rack", filters={"parent": oven_name}, fields=["name"])

	# Auto-assign an idle rack if available
	oven_params.oven = oven_params.oven or str(oven_name)
	oven_params.oven_rack = oven_params.oven_rack or oven_racks[0].name

	now = frappe_utils.now_datetime()
	shifts = frappe.get_list("Attendance Shift", fields=["name"])

	oven_params.date = oven_params.date or now
	oven_params.shift = oven_params.shift or (shifts[0].name if shifts else "")

	oven_params.in_time = oven_params.in_time or now
	oven_params.out_time = oven_params.out_time or now
	oven_params.total_time_in_minutes = oven_params.total_time_in_minutes or 0

	oven_params.slab_top_temp = oven_params.slab_top_temp or 0
	oven_params.slab_bottom_temp = oven_params.slab_bottom_temp or 0
	oven_params.upper_shelf_temp = oven_params.upper_shelf_temp or 0
	oven_params.lower_shelf_temp = oven_params.lower_shelf_temp or 0

	oven_params.top_left_vertex = oven_params.top_left_vertex or 0
	oven_params.top_edge_center = oven_params.top_edge_center or 0
	oven_params.top_right_vertex = oven_params.top_right_vertex or 0
	oven_params.right_edge_centre = oven_params.right_edge_centre or 0
	oven_params.bottom_right_vertex = oven_params.bottom_right_vertex or 0
	oven_params.bottom_edge_centre = oven_params.bottom_edge_centre or 0
	oven_params.bottom_left_vertex = oven_params.bottom_left_vertex or 0
	oven_params.left_edge_centre = oven_params.left_edge_centre or 0

	if not oven_params.name:
		oven_params.insert(ignore_permissions=True)
		oven_params.submit()
	else:
		oven_params.save(ignore_permissions=True)

	heating_slab_history_item = next((h for h in slab.slab_history if h.station == "Heating"), None)
	if heating_slab_history_item and not heating_slab_history_item.oven_params:
		heating_slab_history_item.oven_params = oven_params.name
		slab.save(ignore_permissions=True)


def _create_final_qc(slab_name: str, final_qc: SlabQualityReport | None = None):
	slab: Slab = frappe.get_doc("Slab", slab_name)  # pyright: ignore[reportAssignmentType]
	quality_check_slab_history_item = next((item for item in slab.slab_history if item.station == "Quality Check"), None)
	if quality_check_slab_history_item and not final_qc and quality_check_slab_history_item.quality_report_name:
		final_qc = frappe.get_doc("Slab Quality Report", str(quality_check_slab_history_item.quality_report_name))  # pyright: ignore[reportAssignmentType]

	if not final_qc:
		# If the slab quality report is not provided, create one with default values.
		final_qc = frappe.new_doc("Slab Quality Report") # pyright: ignore[reportAssignmentType]
		if not final_qc:
			raise Exception("Slab Quality Report could not be created.")

	# Get Slab Grade
	mg_settings: MahiGranitesSettings = frappe.get_doc("Mahi Granites Settings") # pyright: ignore[reportAssignmentType]
	grades = mg_settings.grades
	# Get Attendance Shift
	shifts = frappe.get_list("Attendance Shift", fields=["name"])

	final_qc.slab = final_qc.slab or str(slab.name)
	final_qc.slab_template = final_qc.slab_template or slab.template
	final_qc.date = frappe_utils.now_datetime()
	final_qc.job_card = final_qc.job_card or str(slab.last_active_job_card)
	final_qc.grade = final_qc.grade or grades[0].code
	final_qc.shift = final_qc.shift or shifts[0].name
	final_qc.bend = final_qc.bend or 0
	final_qc.slab_length = final_qc.slab_length or 0
	final_qc.slab_thickness = final_qc.slab_thickness or 0
	final_qc.slab_width = final_qc.slab_width or 0

	create_slab_quality_report(str(slab.name), final_qc)
