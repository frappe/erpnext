from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'therapy_plan_template',
		'transactions': [
			{
				'label': _('Therapy Plans'),
				'items': ['Therapy Plan']
			}
		]
	}
