from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'payroll_period',
        'transactions': [
            {
                'label': _('Employee Tax Exemption'),
                'items': ['Employee Tax Exemption Proof Submission', 'Employee Tax Exemption Declaration']
            },
        ],
    }