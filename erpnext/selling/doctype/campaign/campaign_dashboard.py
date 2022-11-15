from frappe import _

def get_data():
	return {
		'fieldname': 'campaign_name',
		'transactions': [
			{
				'label': _('Email Campaigns'),
				'items': ['Email Campaign']
			}
		],
	}
