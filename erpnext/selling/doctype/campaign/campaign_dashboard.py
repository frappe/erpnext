from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'campaign_name',
		'transactions': [
			{
				'label': _('Email Campaigns'),
				'items': ['Email Campaign']
			},
			{
				'label': _('Social Media Campaigns'),
				'items': ['Social Media Post']
			}
		]
	}
