import frappe

# Skips user permission check for doctypes where department link field was recently added
# https://github.com/frappe/erpnext/pull/14121

def execute():
    user_permissions = frappe.get_all("User Permission", filters=[['allow', '=', 'Department']], fields=['name', 'skip_for_doctype'])

    for perm in user_permissions:
        skip_for_doctype = perm.get('skip_for_doctype')
        doctypes_to_skip = ['Appraisal', 'Retention Bonus', 'Compensatory Leave Request', 'Additional Salary Component', 'Shift Request',
            'Leave Allocation', 'Shift Assignment', 'Expense Claim', 'Instructor', 'Salary Slip', 'Employee Tax Exemption Proof Submission',
            'Attendance', 'Training Feedback', 'Employee Incentive', 'Employee Tax Exemption Declaration', 'Training Result Employee',
            'Travel Request', 'Leave Application', 'Employee Advance', 'Activity Cost', 'Salary Structure Assignment','Training Event Employee',
            'Timesheet', 'Employee Transfer', 'Sales Person', 'Employee Benefit Application', 'Attendance Request',
            'Payroll Employee Detail', 'Employee Promotion', 'Leave Encashment', 'Employee Benefit Claim']

        skip_for_doctype = skip_for_doctype.split('\n') + doctypes_to_skip
        skip_for_doctype = set(skip_for_doctype) # to remove duplicates
        skip_for_doctype = '\n'.join(skip_for_doctype) # convert back to string

        frappe.set_value('User Permission', perm.name, 'skip_for_doctype', skip_for_doctype)

