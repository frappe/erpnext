frappe.listview_settings['Healthcare Service Order'] = {
	add_fields: ['name', 'status'],
	filters: [['docstatus', '=', '1']],
	has_indicator_for_cancelled: 1,
	get_indicator: function (doc) {
		return [__(doc.status), {
			'Active': 'blue',
			'On Hold': 'yellow',
			'Completed': 'green',
			'Revoked': 'grey',
			'Replaced': 'grey',
			'Unknown': 'grey',
			'Entered in Error': 'red'
		}[doc.status], 'status,=,' + doc.status];
	}
};