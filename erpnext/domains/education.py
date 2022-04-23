from __future__ import unicode_literals

data = {
	'desktop_icons': [
		'Student',
		'Program',
		'Course',
		'Student Group',
		'Instructor',
		'Fees',
		'Task',
		'ToDo',
		'Education',
		'Student Attendance Tool',
		'Student Applicant'
	],
	'default_portal_role': 'Student',
	'restricted_roles': [
		'Student',
		'Instructor',
		'Academics User',
		'Education Manager'
	],
	'modules': [
		'Education'
	],
	'on_setup': 'erpnext.education.setup.setup_education'

}