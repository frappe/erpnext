import frappe

# Skips user permission check for doctypes where department link field was recently added
# https://github.com/frappe/erpnext/pull/14121

def execute():
    user_permissions = frappe.get_all("User Permission",
        filters=[['allow', '=', 'Department']],
        fields=['name', 'skip_for_doctype'])

    doctypes_to_skip = []

    for doctype in ['Appraisal', 'Leave Allocation', 'Expense Claim', 'Instructor', 'Salary Slip',
                    'Attendance', 'Training Feedback', 'Training Result Employee',
                    'Leave Application', 'Employee Advance', 'Activity Cost', 'Training Event Employee',
                    'Timesheet', 'Sales Person', 'Payroll Employee Detail']:
        if frappe.db.exists('Custom Field', { 'dt': doctype, 'fieldname': 'department'}): continue
        doctypes_to_skip.append(doctype)

    for perm in user_permissions:
        skip_for_doctype = perm.get('skip_for_doctype')

        skip_for_doctype = skip_for_doctype.split('\n') + doctypes_to_skip
        skip_for_doctype = set(skip_for_doctype) # to remove duplicates
        skip_for_doctype = '\n'.join(skip_for_doctype) # convert back to string

        frappe.set_value('User Permission', perm.name, 'skip_for_doctype', skip_for_doctype)

