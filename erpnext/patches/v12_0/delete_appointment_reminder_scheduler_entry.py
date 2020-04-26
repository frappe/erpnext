import frappe

def execute():
    frappe.delete_doc_if_exists('Scheduled Job Type', 'patient_appointment.send_appointment_reminder')
