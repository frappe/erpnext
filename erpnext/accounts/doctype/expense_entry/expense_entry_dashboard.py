from frappe import _

def get_data():
	return {
		'fieldname': 'expense_entry_name',
		'transactions': [
			{
				'label': _('Journal Entries'),
				'items': ['Journal Entry']
			}
		]
	}