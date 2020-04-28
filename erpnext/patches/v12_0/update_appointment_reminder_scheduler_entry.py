import frappe

def execute():
	job = frappe.db.exists('Scheduled Job Type', 'patient_appointment.send_appointment_reminder')
	if job:
		method = 'erpnext.healthcare.doctype.patient_appointment.patient_appointment.send_appointment_reminder'
		frappe.db.set_value('Scheduled Job Type', job, 'method', method)