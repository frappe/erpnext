frappe.listview_settings['Therapy Plan'] = {
	get_indicator: function(doc) {
		var colors = {
			'Completed': 'green',
			'In Progress': 'orange',
			'Not Started': 'red',
			'Cancelled': 'grey'
		};
		return [__(doc.status), colors[doc.status], 'status,=,' + doc.status];
	}
};
