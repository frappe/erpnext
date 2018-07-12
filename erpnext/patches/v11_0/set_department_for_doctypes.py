import frappe

# Set department value based on employee value

def execute():

    doctypes_to_update = ['Appraisal', 'Leave Allocation', 'Expense Claim', 'Instructor', 'Salary Slip',
        'Attendance', 'Training Feedback', 'Training Result Employee',
        'Leave Application', 'Employee Advance', 'Activity Cost', 'Training Event Employee',
        'Timesheet', 'Sales Person', 'Payroll Employee Detail']

    for doctype in doctypes_to_update:
        frappe.db.sql("""
            update `tab%s` dt
            set department=(select department from `tabEmployee` where name=dt.employee)
        """ % doctype)
