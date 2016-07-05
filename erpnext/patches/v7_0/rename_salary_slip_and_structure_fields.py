# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	update_earning_type_and_amount()
	update_deduction_type_and_amount()

def update_earning_type_and_amount():
	if 'e_type' in frappe.db.get_table_columns("Salary Slip Earning"):
		frappe.db.sql("""update `tabSalary Slip Earning` set 
			e_type = earning_type, e_modified_amount = earning_amount
			where e_type is null and earning_type is not null""")

		frappe.db.sql("""update `tabSalary Structure Earning` set e_type = earning_type 
			where e_type is null and earning_type is not null""")

		for dt in ("Salary Slip Earning", "Salary Structure Earning"):
			frappe.reload_doctype(dt)
			rename_field(dt, "e_type", "earning_type")

		rename_field("Salary Slip Earning", "e_modified_amount", "earning_amount")

def update_deduction_type_and_amount():
	if 'd_type' in frappe.db.get_table_columns("Salary Slip Deduction"):
		frappe.db.sql("""update `tabSalary Slip Deduction` set 
			d_type = deduction_type, d_modified_amount = deduction_amount
			where d_type is null and deduction_type is not null""")

		frappe.db.sql("""update `tabSalary Structure Deduction` set d_type = deduction_type 
			where d_type is null and deduction_type is not null""")

		for dt in ("Salary Slip Deduction", "Salary Structure Deduction"):
			frappe.reload_doctype(dt)
			rename_field(dt, "d_type", "deduction_type")
		
		rename_field("Salary Slip Deduction", "d_modified_amount", "deduction_amount")
