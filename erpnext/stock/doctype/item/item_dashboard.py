from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on stock movement. See {0} for details')\
			.format('<a href="#query-report/Stock Ledger">' + _('Stock Ledger') + '</a>'),
		'fieldname': 'item_code',
		'transactions': [
			{
				'label': _('Groups'),
				'items': []
			},
			{
				'label': _('Pricing'),
				'items': ['Pricing Rule']
			},
			{
				'label': _('Sell'),
				'items': ['Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Buy'),
				'items': ['Material Request', 'Supplier Quotation', 'Request for Quotation',
					'Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
			},
			{
				'label': _('Manufacture'),
				'items': ['Production Plan']
			},
			{
				'label': _('Move'),
				'items': ['Stock Entry']
			}
		]
	}
