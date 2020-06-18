import frappe
from datetime import datetime

@frappe.whitelist()
def get_therapy_sessions_count(patient):
	total = frappe.db.count('Therapy Session', filters={
		'docstatus': 1,
		'patient': patient
	})

	month_start = datetime.today().replace(day=1)
	this_month = frappe.db.count('Therapy Session', filters={
		'creation': ['>', month_start],
		'docstatus': 1,
		'patient': patient
	})

	return {
	'total_therapy_sessions': total,
	'therapy_sessions_this_month': this_month
	}