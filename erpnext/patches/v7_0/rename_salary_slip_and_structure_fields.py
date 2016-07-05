# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	for dt in ("Salary Slip Earning", "Salary Slip Deduction", "Salary Structure Earning", "Salary Structure Deduction"):
		frappe.reload_doctype(dt)

		rename_field(dt, "e_type", "earning_type")
		rename_field(dt, "d_type", "deduction_type")

	for dt in ("Salary Slip Earning", "Salary Slip Deduction"):
		rename_field(dt, "e_modified_amount", "earning_amount")
		rename_field(dt, "d_modified_amount", "deduction_amount")