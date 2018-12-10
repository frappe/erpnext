import frappe
from frappe.desk.form.linked_with import get_linked_doctypes

# Skips user permission check for doctypes where department link field was recently added
# https://github.com/frappe/erpnext/pull/14121

def execute():
	doctypes_to_skip = []
	for doctype in ['Appraisal', 'Leave Allocation', 'Expense Claim', 'Instructor', 'Salary Slip',
					'Attendance', 'Training Feedback', 'Training Result Employee',
					'Leave Application', 'Employee Advance', 'Activity Cost', 'Training Event Employee',
					'Timesheet', 'Sales Person', 'Payroll Employee Detail']:
		if frappe.db.exists('Custom Field', { 'dt': doctype, 'fieldname': 'department'}): continue
		doctypes_to_skip.append(doctype)

	frappe.reload_doctype('User Permission')

	user_permissions = frappe.get_all("User Permission",
		filters=[['allow', '=', 'Department'], ['applicable_for', 'in', [None] + doctypes_to_skip]],
		fields=['name', 'applicable_for'])

	user_permissions_to_delete = []
	new_user_permissions_list = []

	for user_permission in user_permissions:
		if user_permission.applicable_for:
			# simply delete user permission record since it needs to be skipped.
			user_permissions_to_delete.append(user_permission.name)
		else:
			# if applicable_for is `None` it means that user permission is applicable for every doctype
			# to avoid this we need to create other user permission records and only skip the listed doctypes in this patch
			linked_doctypes = get_linked_doctypes(user_permission.allow, True).keys()
			applicable_for_doctypes = list(set(linked_doctypes) - set(doctypes_to_skip))

			user_permissions_to_delete.append(user_permission.name)

			for doctype in applicable_for_doctypes:
				if doctype:
					# Maintain sequence (name, user, allow, for_value, applicable_for, apply_to_all_doctypes)
					new_user_permissions_list.append((
						frappe.generate_hash("", 10),
						user_permission.user,
						user_permission.allow,
						user_permission.for_value,
						doctype,
						0
					))

	if new_user_permissions_list:
		frappe.db.sql('''
			INSERT INTO `tabUser Permission`
			(`name`, `user`, `allow`, `for_value`, `applicable_for`, `apply_to_all_doctypes`)
			VALUES {}'''.format(', '.join(['%s'] * len(new_user_permissions_list))),
			tuple(new_user_permissions_list)
		)

	if user_permissions_to_delete:
		frappe.db.sql('DELETE FROM `tabUser Permission` WHERE `name` IN ({})'.format(
			','.join(['%s'] * len(user_permissions_to_delete))
		), tuple(user_permissions_to_delete))