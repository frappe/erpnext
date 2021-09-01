// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Treatment Plan Template', {
	refresh: function (frm) {
		frm.set_query('type', 'items', function () {
			return {
				filters: {
					'name': ['in', ['Lab Test Template', 'Clinical Procedure Template', 'Therapy Type']],
				}
			};
		});
	},
});
