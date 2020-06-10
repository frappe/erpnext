from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'workstation',
		'transactions': [
			{
				'label': _('Master'),
				'items': ['BOM', 'Routing', 'Operation']
			},
			{
				'label': _('Transaction'),
				'items': ['Work Order', 'Job Card', 'Timesheet']
			}
		],
		'disable_create_buttons': ['BOM', 'Routing', 'Operation',
			'Work Order', 'Job Card', 'Timesheet']
	}
