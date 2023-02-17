from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_log',
		'non_standard_fieldnames': {
            'Material Request':'vehicle_log'
		},
		'transactions': [

			{
				'label': _('Reference'),
				'items': ['Material Request','Expense Claim']
			}
   
		]
	}
 