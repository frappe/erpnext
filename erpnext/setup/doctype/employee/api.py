from frappe import frappe


@frappe.whitelist()
def get_current_user_context():
    user = frappe.session.user

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "employee_name", "production_line", "designation", "attendance_shift"],
        as_dict=True
    )

    return employee