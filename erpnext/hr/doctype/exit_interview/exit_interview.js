// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Interview', {
	refresh: function(frm) {

	},

	employee: function(frm) {
		frappe.db.get_value('Employee', frm.doc.employee, 'relieving_date').then(({ relieving_date }) => {
			if (!relieving_date) {
				frappe.throw({
					message: __('Please set the relieving date for employee {0}',
						['<a href="/app/employee/' + frm.doc.employee +'">' + frm.doc.employee + '</a>']),
					title: __('Relieving Date Missing')
				});
			}
		});
	}
});
