import frappe
@frappe.whitelist(allow_guest=True)
def get_context(context):
    email = frappe.form_dict['email']
    appointment_name = frappe.form_dict['appointment']
    if email and appointment_name:
        appointment = frappe.get_doc('Appointment',appointment_name)
        appointment.set_verified(email)
        context.success = True
        return context
    else:
        print('Something not found')
        context.success = False
        return context