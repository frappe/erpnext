from datetime import date, datetime

from frappe import frappe


@frappe.whitelist(allow_guest=True)
def create_slab(line: str):
	new_slab = frappe.new_doc("Slab")
	new_slab.line = line
	new_slab.batch_number = _generate_batch_number(line)
	new_slab.serial_number = _generate_serial_number()
	new_slab.created_on = datetime.now()
	# TODO - Implement this method completely.
	return new_slab


def _generate_batch_number(line: str):
	today = date.today()
	year_code = chr(65 + today.year - 2017)

	# A: Get total days in the year until today
	total_days_so_far = today.timetuple().tm_yday

	# B: Get the total holidays from the first day of the year till today
	year_start = f"{today.year}-01-01"

	# format date as string
	holidays = frappe.db.count(
		"Holiday",
		filters = [
			["holiday_date", "between", [year_start, today.strftime("%Y-%m-%d")]]
		]
	)

	if holidays == 0:
		frappe.throw("No holidays found. Please create a holiday list for the current year.")

	# Calculate A - B
	total_working_days = total_days_so_far - holidays

	return f'{line}{year_code}/{total_working_days:03d}'


def _generate_serial_number():
	today = date.today()
	curr_month = today.month
	curr_year = today.year

	month_start = f"{curr_year}-{curr_month:02d}-01"

	slab_count = frappe.db.count(
		"Slab",
		filters = {
			"created_on": [">=", month_start]
		}
	)

	return slab_count + 1
