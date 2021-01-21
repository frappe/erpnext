// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership Type', {
	refresh: function (frm) {
		frappe.db.get_single_value('Membership Settings', 'enable_razorpay').then(val => {
			if (val) frm.set_df_property('razorpay_plan_id', 'hidden', false);
		});

		frappe.db.get_single_value('Membership Settings', 'enable_invoicing').then(val => {
			if (val) frm.set_df_property('linked_item', 'hidden', false);
		});

		frm.set_query('linked_item', () => {
			return {
				filters: {
					is_stock_item: 0
				}
			};
		});
	}
});
