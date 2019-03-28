// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Letter of Credit', {
	refresh: function(frm) {
		frm.set_df_property("naming_prefix", "read_only", !frm.is_new());
		frm.set_df_property("letter_of_credit_number", "read_only", !frm.is_new());

		if (!frm.is_new()) {
			frm.add_custom_button(__('Update Name'), function () {
				frm.trigger("update_name");
			});
		}
	},

	update_name: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __('Update Name'),
			fields: [
				{
					"label": "Naming Prefix",
					"fieldname": "naming_prefix",
					"fieldtype": "Data",
					"default": frm.doc.naming_prefix
				},
				{
					"label": "Letter of Credit Number",
					"fieldname": "letter_of_credit_number",
					"fieldtype": "Data",
					"reqd": 1,
					"default": frm.doc.letter_of_credit_number
				},
			],
			primary_action: function() {
				var data = d.get_values();
				if(data.naming_prefix === frm.doc.naming_prefix
					&& data.letter_of_credit_number === frm.doc.letter_of_credit_number)
				{
					d.hide();
					return;
				}

				frappe.call({
					method: "erpnext.accounts.doctype.letter_of_credit.letter_of_credit.update_name",
					args: {
						name: frm.doc.name,
						naming_prefix: data.naming_prefix,
						letter_of_credit_number: data.letter_of_credit_number
					},
					callback: function(r) {
						if(!r.exc) {
							if(r.message) {
								frappe.set_route("Form", "Letter of Credit", r.message);
							} else {
								frm.set_value("naming_prefix", data.naming_prefix);
								frm.set_value("letter_of_credit_number", data.letter_of_credit_number);
							}
							d.hide();
						}
					}
				});
			},
			primary_action_label: __('Update')
		});
		d.show();
	}
});
