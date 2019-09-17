// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Type', {
	refresh: function(frm) {
		if(!frm.is_new()) {
			frm.add_custom_button(__('Update Loan Security Price'), function() {
				frm.trigger('update_price');
			});
		}
	},

	update_price: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __('Update Loan Security Price'),
			fields: [
				{
					"label" : "From Time",
					"fieldname": "from_time",
					"fieldtype": "Datetime",
					"reqd": 1,
					"default": frappe.datetime.now_datetime()
				},
				{
					"label" : "To Time",
					"fieldname": "to_time",
					"fieldtype": "Datetime",
					"reqd": 1,
					"default": frappe.datetime.add_days(frappe.datetime.now_datetime(), 1)
				}

			],
			primary_action: function() {
				var data = d.get_values();
				frappe.call({
					method: "erpnext.loan_management.doctype.loan_security_price.loan_security_price.update_loan_security_price",
					args: {
						'from_timestamp': data.from_time,
						'to_timestamp': data.to_timestamp,
						'loan_type': frm.doc.name
					},
				});
				d.hide();
			},
			primary_action_label: __('Update')
		});
		d.show();
	}
});
