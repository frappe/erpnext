frappe.listview_settings['Supplier Scorecard'] = {
	add_fields: ["indicator_color", "status"],
		get_indicator: function(doc) {
		debugger;
		if (doc.indicator_color) {
			return [__(doc.status), doc.indicator_color.toLowerCase(), "status,=," + doc.status];
		} else {
			return [__('Unknown'), 'darkgrey', "status,=,''"];
		}
	},

};
