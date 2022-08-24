from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'payment_entry',
		'transactions': [
			{
				'label': _('Advances'),
				'items': ['Apply Payment Entries Without References']
			},
        ]
	}
