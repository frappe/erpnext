from frappe import _

def get_data():
	return {
		'fieldname': 'allocation_period',
		'transactions': [
			{
				'label': _('Allocations'),
				'items': ['Vehicle Allocation']
			},
		]
	}
