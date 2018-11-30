from frappe import _


def get_data():
	return {
		'fieldname': 'delivery_trip',
		'non_standard_fieldnames': {
			'Payment Entry': 'reference_no',
		},
		'internal_links': {
			'Delivery Note': ['delivery_stops', 'delivery_note'],
			'Sales Invoice': ['delivery_stops', 'sales_invoice']
		},
		'transactions': [
			{
				'label': _('Sales'),
				'items': ['Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Payments'),
				'items': ['Payment Entry']
			}
		]
	}
