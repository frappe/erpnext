import frappe

def execute():
    frappe.reload_doctype('Employee')
    has_subordinates = frappe.db.sql_list("""select reports_to from `tabEmployee` where reports_to is not null""")
    has_subordinates = list(set(has_subordinates))

    for d in has_subordinates:
        frappe.db.set_value('Employee', d, 'has_subordinates', 1)