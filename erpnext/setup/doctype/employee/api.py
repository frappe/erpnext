from frappe import frappe


@frappe.whitelist()
def get_current_user_context() -> dict[str, str]:
    user = frappe.session.user

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "employee_name", "production_line", "designation", "attendance_shift", "workstation_type"],
        as_dict=True
    )

    return employee
