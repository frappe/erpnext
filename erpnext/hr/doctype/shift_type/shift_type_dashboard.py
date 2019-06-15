from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'shift_type',
        'transactions': [
            {
                'items': ['Shift Request', 'Shift Assignment']
            }
        ],
    }