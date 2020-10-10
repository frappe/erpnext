from __future__ import unicode_literals

def get_data():
	return {
		'fieldname': 'vehicle',
		'transactions': [
			{
				'label': ['Sales'],
				'items': ['Delivery Note', 'Sales Invoice']
			},
			{
				'label': ['Purchase'],
				'items': ['Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': ['Movement'],
				'items': ['Stock Entry']
			},
			{
				'label': ['Reference'],
				'items': ['Vehicle Log', 'Serial No']
			},
		]
	}