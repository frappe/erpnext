from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("Time Log"):
		timesheet = frappe.db.sql("""SELECT ts.name AS name, tl.name AS timelogname,
				tl.modified AS modified, tl.modified_by AS modified_by, tl.creation AS creation, tl.owner AS owner
			FROM
				`tabTimesheet` ts, `tabTimesheet Detail` tsd, `tabTime Log` tl
			WHERE
				tsd.parent = ts.name AND tl.from_time = tsd.from_time AND tl.to_time = tsd.to_time
				AND tl.hours = tsd.hours AND tl.billing_rate = tsd.billing_rate AND tsd.idx=1
				AND tl.docstatus < 2""", as_dict=1)

		for data in timesheet:
			frappe.db.sql(""" update `tabTimesheet` set creation = %(creation)s,
				owner = %(owner)s, modified = %(modified)s, modified_by = %(modified_by)s
				where name = %(name)s""", data)

			frappe.db.sql("""
				update
					`tabDynamic Link`
				set
					link_doctype = "Timesheet", link_name = %(timesheet)s
				where
					link_doctype = "Time Log" and link_name = %(timelog)s
			""", {'timesheet': data.name, 'timelog': data.timelogname}, auto_commit=1)
