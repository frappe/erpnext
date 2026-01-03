from datetime import date, datetime
from typing import Any

from frappe import frappe
from frappe.query_builder.functions import Count

from erpnext.manufacturing.doctype.slab.slab import ALLOWED_STAGES, Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory


# TODO: Remove allow_guest after testing.
@frappe.whitelist(allow_guest=True)
def create_slab(line: str, type: str, job_card_number: str | None = None):
    new_slab: Slab = frappe.new_doc("Slab")  # pyright: ignore[reportAssignmentType]
    new_slab.line = line
    new_slab.template = type
    new_slab.current_job_card = job_card_number
    new_slab.batch_number = _generate_batch_number(line)

    slab_number: int = _get_slab_number()
    new_slab.number = slab_number
    new_slab.serial_number = f"{slab_number:04d}"

    new_slab.created_on = datetime.now()
    current_stage = ALLOWED_STAGES[0]
    new_slab.current_stage = (
        current_stage  # pyright: ignore[reportAttributeAccessIssue]
    )

    # Create the first line item for the slab history as distribution.
    slab_history: SlabHistory = frappe.new_doc(
        "Slab History"
    )  # pyright: ignore[reportAssignmentType]
    slab_history.station = current_stage
    slab_history.in_time = datetime.now()
    slab_history.job_card_number = job_card_number
    new_slab.slab_history.append(slab_history)

    # TODO: Remove ignore_permissions after testing.
    new_slab.save(ignore_permissions=True)
    return new_slab


# TODO: Remove allow_guest after testing.
@frappe.whitelist(allow_guest=True)
def checkout_slab(slab_number: str):
    slab: Slab = frappe.get_doc(
        "Slab", slab_number
    )  # pyright: ignore[reportAssignmentType]

    # Get the last item in slab history
    last_history = slab.slab_history[-1]

    # Check if the out time on the last history item is None
    if last_history.out_time is not None:
        frappe.throw("Slab is already checked out of the current station.")

    last_history.out_time = datetime.now()
    last_history.total_time_in_minutes = (
        last_history.out_time - last_history.in_time
    ).total_seconds() / 60  # pyright: ignore[reportOperatorIssue]

    # TODO: Remove ignore_permissions after testing.
    slab.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def move_slab_to(
    slab_number: str,
    next_stage: str,
    job_card_number: str | None = None,
    checkout_and_move=True,
):
    # Validation: Check if the given stage is valid.
    if next_stage not in ALLOWED_STAGES:
        frappe.throw("Invalid next stage")

    slab: Slab = frappe.get_doc("Slab", slab_number)

    current_stage_index = ALLOWED_STAGES.index(slab.current_stage)
    next_stage_index = ALLOWED_STAGES.index(next_stage)

    # Validation: Check the direction of transition
    if next_stage_index < current_stage_index or (
        next_stage_index == current_stage_index and next_stage != "Re-pressing"
    ):
        frappe.throw(
            f"Invalid stage transition: cannot move from {slab.current_stage} to {next_stage}"
        )

    # If the slab is not checked out yet, check it out of the previous
    # stage before moving it to the next stage, based on the flag set.
    last_history = slab.slab_history[-1]
    if last_history.out_time is None:
        if not checkout_and_move:
            frappe.throw("Cannot move slab without checking out")

        checkout_slab(slab_number)
        slab: Slab = frappe.get_doc("Slab", slab_number)

    slab.current_stage = next_stage  # pyright: ignore[reportAttributeAccessIssue]
    slab.current_job_card = job_card_number

    # Append the next stage to the slab history.
    slab_history: SlabHistory = frappe.new_doc(
        "Slab History"
    )  # pyright: ignore[reportAssignmentType]
    slab_history.station = next_stage
    slab_history.in_time = datetime.now()
    slab_history.job_card_number = job_card_number
    slab.slab_history.append(slab_history)

    # TODO: Remove ignore_permissions after testing.
    slab.save(ignore_permissions=True)


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
        frappe.throw(
            "No holidays found. Please create a holiday list for the current year."
        )

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

    slab_count = (
        frappe.db.count("Slab", filters={"created_on": [">=", month_start]}) + 1
    )
    return slab_count
