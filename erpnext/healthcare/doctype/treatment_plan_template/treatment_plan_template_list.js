frappe.listview_settings['Treatment Plan Template'] = {
	get_indicator: function(doc) {
		var colors = {
			1: 'gray',
			0: 'blue',
		};
		let label  = doc.disabled == 1 ? 'Disabled' : 'Enabled';
		return [__(label), colors[doc.disabled], 'disable,=,' + doc.disabled];
	}
};
