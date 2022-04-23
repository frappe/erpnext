# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'room',
		'transactions': [
			{
				'label': _('Course'),
				'items': ['Course Schedule']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Plan']
			}
		]
	}