from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'training_event',
        'transactions': [
            {
                'items': ['Training Result', 'Training Feedback']
            },
        ],
    }