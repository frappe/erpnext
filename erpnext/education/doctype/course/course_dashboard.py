# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'course',
		'non_standard_fieldnames': {
		},
		'transactions': [
			{
				'label': _('Course'),
				'items': ['Course Enrollment', 'Course Schedule']
			},
			{
				'label': _('Student'),
				'items': ['Student Group']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Plan']
			},
		]
	}