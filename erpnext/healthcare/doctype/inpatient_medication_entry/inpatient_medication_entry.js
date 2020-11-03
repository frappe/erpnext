// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inpatient Medication Entry', {
	refresh: function(frm) {
		// Ignore cancellation of doctype on cancel all
		frm.ignore_doctypes_on_cancel_all = ['Stock Entry'];

		frm.set_query('item_code', () => {
			return {
				filters: {
					is_stock_item: 1
				}
			};
		});

		frm.set_query('drug_code', 'medication_orders', () => {
			return {
				filters: {
					is_stock_item: 1
				}
			};
		});
	},

	get_medication_orders: function(frm) {
		frappe.call({
			method: 'get_medication_orders',
			doc: frm.doc,
			freeze: true,
			freeze_message: __('Fetching Pending Medication Orders'),
			callback: function() {
				refresh_field('medication_orders');
			}
		});
	}
});
