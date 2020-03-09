frappe.listview_settings['Fee Validity'] = {
	get_indicator: function(doc) {
		var colors = {
			'Ongoing': 'orange',
			'Completed': 'green',
			'Expired': 'grey'
		};
		return [__(doc.status), colors[doc.status], 'status,=,' + doc.status];
	}
};
