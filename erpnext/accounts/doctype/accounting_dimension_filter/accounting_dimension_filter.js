// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounting Dimension Filter', {
	onload: function(frm) {
		frappe.db.get_list('Accounting Dimension',
			{fields: ['name']}).then((res) => {
				let options = ['Cost Center', 'Project'];

				res.forEach((dimension) => {
					options.push(dimension.name);
				});

				frm.set_df_property('accounting_dimension', 'options', options);
		});
	},

	accounting_dimension: function(frm) {
		frm.clear_table("dimensions");
		let row = frm.add_child("dimensions");
		row.accounting_dimension = frm.doc.accounting_dimension;
		frm.refresh_field("dimensions");
	},
});

frappe.ui.form.on('Allowed Dimension', {
	dimensions_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.accounting_dimension = frm.doc.accounting_dimension;
		frm.refresh_field("dimensions");
	}
});