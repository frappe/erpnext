def get_data():
	return {
		'fieldname': 'asset_name',
		'non_standard_fieldnames': {
			'Asset Movement': 'asset'
		},
		'transactions': [
			{
				'label': ['Maintenance'],
				'items': ['Asset Maintenance', 'Asset Maintenance Log']
			},
			{
				'label': ['Repair'],
				'items': ['Asset Repair']
			},
			{
				'label': ['Movement'],
				'items': ['Asset Movement']
			}
		]
	}