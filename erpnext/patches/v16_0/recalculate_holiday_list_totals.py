import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Sum


def execute():
	holiday_list = frappe.qb.DocType("Holiday List")
	holiday = frappe.qb.DocType("Holiday")
	total_holidays = (
		frappe.qb.from_(holiday)
		.select(Sum(Case().when(holiday.is_half_day == 1, 0.5).else_(1)))
		.where(
			(holiday.parent == holiday_list.name)
			& (holiday.parenttype == "Holiday List")
			& (holiday.parentfield == "holidays")
		)
	)
	frappe.qb.update(holiday_list).set(holiday_list.total_holidays, Coalesce(total_holidays, 0)).run()
