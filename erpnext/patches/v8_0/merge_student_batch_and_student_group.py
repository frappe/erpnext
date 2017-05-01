# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():

	# for deleting the student batch creation tool
	frappe.delete_doc("DocType", "Student Batch Creation Tool", force=1)
	frappe.db.sql("drop table if exists `Student Batch Creation Tool`")