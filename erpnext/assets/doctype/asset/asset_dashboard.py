<<<<<<< HEAD

=======
from frappe import _
>>>>>>> 16de29a3cb (fix(translation) - correction for translation)

def get_data():
	return {
		'non_standard_fieldnames': {
			'Asset Movement': 'asset'
		},
		'transactions': [
			{
				'label': _('Movement'),
				'items': ['Asset Movement']
			}
		]
	}
