
from frappe import _


def get_data():
	return {
		'fieldname': 'pos_profile',
		'transactions': [
			{
				'items': ['Sales Invoice', 'POS Closing Voucher']
			}
		]
	}
