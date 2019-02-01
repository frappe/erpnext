from frappe import _

def get_data():
    return {
        'fieldname': 'review',
        'transactions': [
            {
                'label': _('Action'),
                'items': ['Quality Action']
            },
            {
                'label': _('Meeting'),
                'items': ['Quality Meeting']
            }
        ],
    }