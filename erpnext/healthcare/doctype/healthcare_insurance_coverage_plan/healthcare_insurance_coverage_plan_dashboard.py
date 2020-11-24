from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'healthcare_insurance_coverage_plan',
		'transactions': [
			{
				'items': ['Healthcare Service Insurance Coverage', 'Healthcare Insurance Subscription']
			}
		]
	}
