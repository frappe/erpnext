// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Party Link', {
	refresh: function(frm) {
		frm.set_query('primary_role', () => {
			return {
				filters: {
					name: ['in', ['Customer', 'Supplier']]
				}
			};
		});

		frm.set_query('secondary_role', () => {
			let party_types = Object.keys(frappe.boot.party_account_types)
				.filter(p => p != frm.doc.primary_role);
			return {
				filters: {
					name: ['in', party_types]
				}
			};
		});
	},

	primary_role(frm) {
		frm.set_value('primary_party', '');
		frm.set_value('secondary_role', '');
	},

	secondary_role(frm) {
		frm.set_value('secondary_party', '');
	}
});
