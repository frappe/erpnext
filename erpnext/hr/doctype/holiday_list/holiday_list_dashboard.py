def get_data():
	return {
		'fieldname': 'holiday_list',
		'non_standard_fieldnames': {
			'Company': 'default_holiday_list',
			'Leave Period': 'optional_holiday_list'
		},
		'transactions': [
			{
				'items': ['Company', 'Employee', 'Workstation'],
			},
			{
				'items': ['Leave Period', 'Shift Type']
			}
		]
	}