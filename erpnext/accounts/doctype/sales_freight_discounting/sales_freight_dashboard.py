from __future__ import unicode_literals
from frappe import _
import frappe

def get_data():
    return {
		'fieldname': 'name',
		'non_standard_fieldnames': {
			'Journal Entry': 'journal_entry_name',
			},
		'transactions': [
			{
				'label': _('Accounts'),
				'items': ['Journal Entry']
			},
		]
	}
