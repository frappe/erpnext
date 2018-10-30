from frappe import _

def get_data():
    return {
        'fieldname': 'procedure',
        'transactions': [
            {
                'label': _('Goal'),
                'items': ['Quality Goal']
            },  
            {
                'label': _('Review'),
                'items': ['Quality Review']
            },
            {
                'label': _('Action'),
                'items': ['Quality Action']
            }
        ],
    }