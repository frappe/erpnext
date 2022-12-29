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

def update_benefit_type_name():
    bt = frappe.db.sql("""
        select name, benefit_type from `tabEmployee Benefit Type`;
    """, as_dict=True)
    if bt:
        for a in bt:
            frappe.db.sql("update `tabEmployee Benefit Type` set name = '{}' where name = '{}'".format(a.benefit_type, a.name))
            print(a.name)

def update_department():
    el = frappe.db.sql("""
        select name from `tabEmployee`
        where department = 'Habrang & Tshophangma Coal Mine - SMCL'
        and status = 'Active'
    """,as_dict=1)
    if el:
        for a in el:
            frappe.db.sql("""
                update `tabEmployee` set department = 'PROJECTS & MINES DEPARTMENT - SMCL'
                where name = '{}'
            """.format(a.name))
            print(a.name)

def update_user_pwd():
	user_list = frappe.db.sql("select name from `tabUser` where name not in ('Administrator', 'Guest')", as_dict=1)
	c = 1
    non_employee = []
	for i in user_list:
		# print("NAME '{}':  '{}'".format(c,str(i.name)))
        emp = frappe.get_doc("Employee", {"user_id":i.name})
        if not employee:
            non_employee.append(i.name)
		# ds = frappe.get_doc("User", i.name)
		# ds.new_password = 'smcl@2022'
		# ds.save(ignore_permissions=1)
		# c += 1
    if len(non_employee) > 0:
    	print("Non Employee Users: "+str(non_employee))