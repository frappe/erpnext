from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'training_event',
        'transactions': [
            {
                'label': _('Result And Feedback'),
                'items': ['Training Result', 'Training Feedback']
            },
        ],
    }