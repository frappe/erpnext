from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update 
		`tabTimesheet` as ts,
		(
			select min(from_time)as from_time, max(to_time) as to_time, parent from `tabTimesheet Detail` group by parent
		) as tsd
		set ts.status = 'Submitted', ts.start_date = tsd.from_time, ts.end_date = tsd.to_time 
		where tsd.parent = ts.name and ts.status = 'Draft' and ts.docstatus =1""")