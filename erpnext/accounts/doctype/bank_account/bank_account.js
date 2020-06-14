// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Account', {
	setup: function(frm) {
		frm.set_query("account", function() {
			return {
				filters: {
					'account_type': 'Bank',
					'company': frm.doc.company,
					'is_group': 0
				}
			};
		});
		frm.set_query("party_type", function() {
			return {
				query: "erpnext.setup.doctype.party_type.party_type.get_party_type",
			};
		});
	},
	refresh: function(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Bank Account' }

		frm.toggle_display(['address_html','contact_html'], !frm.doc.__islocal);

		if (frm.doc.__islocal) {
			frappe.contacts.clear_address_and_contact(frm);
		}
		else {
			frappe.contacts.render_address_and_contact(frm);
		}

		if (frm.doc.integration_id) {
			frm.add_custom_button(__("Unlink external integrations"), function() {
				frappe.confirm(__("This action will unlink this account from any external service integrating ERPNext with your bank accounts. It cannot be undone. Are you certain ?"), function() {
					frm.set_value("integration_id", "");
				});
			});
		}
	},

	is_company_account: function(frm) {
		frm.set_df_property('account', 'reqd', frm.doc.is_company_account);
	}
});
