from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'operation',
		'transactions': [
			{
				'label': _('Manufacture'),
				'items': ['BOM', 'Work Order', 'Job Card', 'Timesheet']
			}
		]
	}
