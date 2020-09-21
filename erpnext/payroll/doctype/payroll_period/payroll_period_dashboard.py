from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'payroll_period',
        'transactions': [
            {
                'items': ['Employee Tax Exemption Proof Submission', 'Employee Tax Exemption Declaration']
            },
        ],
    }