frappe.listview_settings['Clinical Procedure'] = {
	get_indicator: function(doc) {
		var colors = {
			'Completed': 'green',
			'In Progress': 'orange',
			'Pending': 'orange',
			'Cancelled': 'grey'
		};
		return [__(doc.status), colors[doc.status], 'status,=,' + doc.status];
	}
};
