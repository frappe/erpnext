import frappe
from frappe.utils import add_months, getdate


def execute():
	# This fix is not related to Party Specific Item,
	# but it is needed for code introduced around that time
	# If your DB doesn't have this doctype yet, you should be fine
	if not frappe.db.exists("DocType", "Party Specific Item"):
		return

	for doctype in ("Purchase Invoice", "Sales Invoice"):
		# invoices to update = overdue + mod 6 months ago (1 apr 2021)
		# OR modified after PR date (25 sept 2021) + overdue or partly paid or overdue and discounted or partly paid and discounted
		frappe.db.query("""
			SELECT name
			FROM `tab{}`
			WHERE (
					docstatus = `Overdue`
					AND modified > %s
				)
				OR (
					docstatus IN (`Overdue`, `Partly Paid`, `Overdue and Discounted`, `Partly Paid and Discounted`)
					AND modified > %s
				)
		""".format(doctype),(add_months(getdate(), -6), getdate("2021-09-25")))
		# for docname in get_all:
		# 	doc = frappe.get_doc(doctype, docname)
		# 	doc.set_status()

		# create dict of docs, update in one go