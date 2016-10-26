from frappe import _

data = {
	'heatmap': True,
	'heatmap_message': _('This is based on logs against this Vehicle. See timeline below for details'),
	'fieldname': 'license_plate',
	'transactions': [
		{
			'label': _('Logs'),
			'items': ['Vehicle Log']
		}
	]
}