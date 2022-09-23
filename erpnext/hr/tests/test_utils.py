import frappe
from frappe.utils import get_first_day, get_last_day, getdate


def get_first_sunday(holiday_list="Salary Slip Test Holiday List", for_date=None):
	date = for_date or getdate()
	month_start_date = get_first_day(date)
	month_end_date = get_last_day(date)
	first_sunday = frappe.db.sql(
		"""
		select holiday_date from `tabHoliday`
		where parent = %s
			and holiday_date between %s and %s
		order by holiday_date
	""",
		(holiday_list, month_start_date, month_end_date),
	)[0][0]

	return first_sunday
