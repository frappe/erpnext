from __future__ import unicode_literals

import frappe

def execute():
	for dt in ("Customer", "Customer Group", "Company"):
		frappe.reload_doctype(dt, force=True)
		frappe.db.sql("""update `tab{0}` set credit_days_based_on='Fixed Days'
			where ifnull(credit_days, 0) > 0""".format(dt))
