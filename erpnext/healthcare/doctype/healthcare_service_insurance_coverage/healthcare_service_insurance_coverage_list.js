frappe.listview_settings['Healthcare Service Insurance Coverage'] = {
	add_fields: ['is_active'],
	get_indicator: function(doc) {
		if (doc.is_active) {
			return [__('Active'), 'green', 'is_active,=,Yes'];
		} else {
			return [__('Not Active'), 'grey', 'is_active,=,No'];
		}
	}
};
