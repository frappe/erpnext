from __future__ import unicode_literals

import frappe


def execute():
	if frappe.db.table_exists("Offer Letter") and not frappe.db.table_exists("Job Offer"):
		frappe.rename_doc("DocType", "Offer Letter", "Job Offer", force=True)
		frappe.rename_doc("DocType", "Offer Letter Term", "Job Offer Term", force=True)
		frappe.reload_doc("hr", "doctype", "job_offer")
		frappe.reload_doc("hr", "doctype", "job_offer_term")
		frappe.delete_doc("Print Format", "Offer Letter")
