// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Payroll Entry'] = {
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		var status_color = {
			'Draft': 'red',
			'Submitted': 'blue',
			'Queued': 'orange',
			'Failed': 'red',
			'Cancelled': 'red'

		};
		return [__(doc.status), status_color[doc.status], 'status,=,'+doc.status];
	}
};
