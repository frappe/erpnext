// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Group', {
	setup(frm) {
		frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				filters: {
					'account_type': 'Receivable',
					'company': d.company,
					'is_group': 0
				}
			}
		}
	},
});
