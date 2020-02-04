from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
        'reports': [
			{
                'label': _('Reports'),
				'items': ['Employee Leave Balance']
			}
		]
    }