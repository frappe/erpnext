from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'insurance_company',
		'transactions': [
			{
				'items': ['Healthcare Insurance Contract', 'Healthcare Insurance Coverage Plan', 'Healthcare Insurance Subscription']
			}
		]
	}
