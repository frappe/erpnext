from frappe import _

def get_data():
    return {
        'fieldname': 'feedback',
        'transactions': [
            {
                'label': _('Action'),
                'items': ['Quality Action']
            }
        ],
    }