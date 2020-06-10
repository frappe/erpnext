from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'loan_application',
        'transactions': [
            {
                'items': ['Loan', 'Loan Security Pledge']
            },
        ],
    }