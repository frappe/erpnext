from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Company. See timeline below for details'),

		'graph': True,
		'graph_method': "frappe.utils.goal.get_monthly_goal_graph_data",
		'graph_method_args': {
			'title': 'Sales',
			'goal_value_field': 'sales_target',
			'goal_total_field': 'total_monthly_sales',
			'goal_history_field': 'sales_monthly_history',
			'goal_doctype': 'Sales Invoice',
			'goal_doctype_link': 'company',
			'goal_field': 'base_grand_total',
			'date_field': 'posting_date',
			'filter_str': 'status != "Draft"',
			'aggregation': 'sum'
		},

		'fieldname': 'company',
		'transactions': [
			{
				'label': _('Pre Sales'),
				'items': ['Quotation']
			},
			{
				'label': _('Orders'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Support'),
				'items': ['Issue']
			},
			{
				'label': _('Projects'),
				'items': ['Project']
			}
		]
	}