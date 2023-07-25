frappe.listview_settings['Process Payment Reconciliation'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		let colors = {
			'Queued': 'orange',
			'Paused': 'orange',
			'Completed': 'green',
			'Partially Reconciled': 'orange',
			'Running': 'blue',
			'Failed': 'red',
		};
		let status = doc.status;
		return [__(status), colors[status], 'status,=,'+status];
	},
};
