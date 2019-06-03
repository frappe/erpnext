from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'job_applicant',
        'transactions': [
            {
                'label': _('Employee'),
                'items': ['Employee', 'Employee Onboarding']
            },
            {
                'items': ['Job Offer']
            },
        ],
    }