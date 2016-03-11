from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Holiday List")

	default_holiday_list = frappe.db.get_value("Holiday List", {"is_default": 1})
	if default_holiday_list:
		for company in frappe.get_all("Company", fields=["name", "default_holiday_list"]):
			if not company.default_holiday_list:
				frappe.db.set_value("Company", company.name, "default_holiday_list", default_holiday_list)


	fiscal_years = frappe._dict((fy.name, fy) for fy in frappe.get_all("Fiscal Year", fields=["name", "year_start_date", "year_end_date"]))

	for holiday_list in frappe.get_all("Holiday List", fields=["name", "fiscal_year"]):
		fy = fiscal_years[holiday_list.fiscal_year]
		frappe.db.set_value("Holiday List", holiday_list.name, "from_date", fy.year_start_date)
		frappe.db.set_value("Holiday List", holiday_list.name, "to_date", fy.year_end_date)
