from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This covers all scorecards tied to this Setup'),
		'fieldname': 'supplier',
		'method' : 'erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.get_timeline_data',
		'transactions': [
			{
				'label': _('Scorecards'),
				'items': ['Supplier Scorecard Period']
			}
		]
	}
