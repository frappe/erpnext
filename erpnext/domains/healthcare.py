data = {
	'desktop_icons': [
		'Patient',
		'Patient Appointment',
		'Consultation',
		'Lab Test',
		'Healthcare',
		'Accounts',
		'Buying',
		'Stock',
		'HR',
		'ToDo'
	],
	'default_portal_role': 'Patient',
	'restricted_roles': [
		'Healthcare Administrator',
		'LabTest Approver',
		'Laboratory User',
		'Nursing User',
		'Physician',
		'Patient'
	],
	'custom_fields': {
		'Sales Invoice': dict(fieldname='appointment', label='Patient Appointment',
			fieldtype='Link', options='Patient Appointment',
			insert_after='customer')
	},
	'on_setup': 'erpnext.healthcare.setup.setup_healthcare'
}