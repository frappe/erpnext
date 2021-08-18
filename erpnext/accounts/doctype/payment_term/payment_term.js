// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Payment Term', {
	onload(frm) {
		frm.trigger('set_dynamic_description');
	},
	discount(frm) {
		frm.trigger('set_dynamic_description');
	},
	discount_type(frm) {
		frm.trigger('set_dynamic_description');
	},
	set_dynamic_description(frm) {
		if (frm.doc.discount) {
			let description = __("{0}% of total invoice value will be given as discount.", [frm.doc.discount]);
			if (frm.doc.discount_type == 'Amount') {
				description = __("{0} will be given as discount.", [fmt_money(frm.doc.discount)]);
			}
			frm.set_df_property("discount", "description", description);
		}
	}
});