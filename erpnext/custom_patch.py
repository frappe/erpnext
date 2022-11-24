import frappe
from erpnext.setup.doctype.employee.employee import create_user
def create_users():
    print("here")

    employees = frappe.db.sql("""
        select name from `tabEmployee` where company_email is not NULL and user_id is NULL
    """,as_dict=1)
    if employees:
        for a in employees:
            employee = frappe.get_doc("Employee", a.name)
            if not frappe.db.exists("User",employee.company_email):
                create_user(a.name, email = employee.company_email)
                print("User created for employee {}".format(a.name))
                employee.db_set("user_id", employee.company_email)
    frappe.db.commit()

def update_employee_user_id():
    print()
    users = frappe.db.sql("""
        select name from `tabUser`
    """,as_dict=1)
    if users:
        for a in users:
            employee = frappe.db.get_value("Employee",{"company_email":a.name},"name")
            if employee:
                employee_doc = frappe.get_doc("Employee",employee)
                employee_doc.db_set("user_id",a.name)
                print("Updated email for "+str(a.name))
    frappe.db.commit()