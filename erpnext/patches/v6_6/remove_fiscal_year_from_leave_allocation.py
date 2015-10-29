from __future__ import unicode_literals
import frappe

def execute():
	for leave_allocation in frappe.db.sql("select name, fiscal_year from `tabLeave Allocation`", as_dict=True):
		year_start_date, year_end_date = frappe.db.get_value("Fiscal Year", leave_allocation["fiscal_year"],
			["year_start_date", "year_end_date"])
		
		frappe.db.sql("""update `tabLeave Allocation` 
			set from_date=%s, to_date=%s where name=%s""", 
			(year_start_date, year_end_date, leave_allocation["name"]))
			
		frappe.db.commit()
			
		