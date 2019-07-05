from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'workstation',
		'transactions': [
			{
				'label': _('Manufacture'),
				'items': ['BOM', 'Routing', 'Work Order', 'Job Card', 'Operation', 'Timesheet']
			}
		]
	}
