# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import *

def execute():

	# for deleting the student batch creation tool
	frappe.delete_doc("DocType", "Student Batch Creation Tool", force=1)
	frappe.db.sql("drop table if exists `Student Batch Creation Tool`")

	# changing the student batch to student group in the student attendance
	frappe.reload_doctype("Student Attendance")

	table_columns = frappe.db.get_table_columns("Student Attendance")
	if "student_batch" in table_columns:
		rename_field("Student Attendance", "student_batch", "student_group")
