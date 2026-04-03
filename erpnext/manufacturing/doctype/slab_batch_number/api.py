
from datetime import date, datetime

import frappe

from erpnext.accounts.doctype.fiscal_year.fiscal_year import FiscalYear


# This will run once every hour on the first day of the month.
def delete_all_batch_numbers():
	today = datetime.now()
	frappe.logger().info("Scheduler fired for deleting slab batch numbers")
	frappe.msgprint(f"Running delete_all_batch_numbers on {today.strftime('%Y-%m-%d')}")
	# A: Get the current fiscal year
	fiscal_years: list = frappe.db.get_all(
		"Fiscal Year",
		filters=[["year_start_date", "<=", today], ["year_end_date", ">=", today]],
		fields=["year_start_date", "year_end_date"],
		ignore_permissions=True,
	)  # pyright: ignore[reportAssignmentType]

	if not fiscal_years:
		frappe.throw("No fiscal year found for the current date.", frappe.ValidationError)

	fiscal_year: FiscalYear = fiscal_years[0]

	attendance_shifts = frappe.db.get_all(
		"Attendance Shift",
		fields=["name", "start_time", "end_time", "does_span_next_day"],
		limit=1,
		order_by="start_time ASC",
		ignore_permissions=True,
	)

	first_shift = attendance_shifts[0] if attendance_shifts else None
	first_shift_start_hour = first_shift.start_time.seconds / 3600 if first_shift else 0
	year_start_date: datetime = fiscal_year.year_start_date  # pyright: ignore[reportAssignmentType]

	is_first_hour_of_fy = today.year == year_start_date.year and today.month == year_start_date.month and today.day == year_start_date.day and today.hour == first_shift_start_hour
	if not is_first_hour_of_fy:
		return

	delete_batch_numbers_older_than(year_start_date)


def delete_batch_numbers_older_than(ref_date: date):
	batch_numbers_of_previous_year = frappe.db.count("Slab Batch Number", filters={"date": ["<", ref_date.strftime("%Y-%m-%d")]})
	if not batch_numbers_of_previous_year:
		return

	frappe.db.sql("DELETE FROM `tabSlab Batch Number` WHERE date < %s", (ref_date.strftime("%Y-%m-%d"),))

	# After deleting the old slabs, reset the naming series counter to 0.
	batch_prefix = frappe.get_meta("Slab Batch Number").autoname.split(".")[0]  # pyright: ignore[reportAttributeAccessIssue]
	frappe.db.sql("""
        UPDATE `tabSeries`
        SET `current` = %s
        WHERE `name` = %s
    """, (0, batch_prefix))

	frappe.db.commit()
