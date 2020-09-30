// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Order', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1) {
			frm.trigger("show_progress");
		}
	},

	show_progress: function(frm) {
		let bars = [];
		let message = '';
		let added_min = false;

		// completed sessions
		let title = __('{0} medication orders completed', [frm.doc.completed_orders]);
		if (frm.doc.completed_orders === 1) {
			title = __('{0} medication order completed', [frm.doc.completed_orders]);
		}
		title += __(' out of {0}', [frm.doc.total_orders]);

		bars.push({
			'title': title,
			'width': (frm.doc.completed_orders / frm.doc.total_orders * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
			added_min = 0.5;
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	}
});
