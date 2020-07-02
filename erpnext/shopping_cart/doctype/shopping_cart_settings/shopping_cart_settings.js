// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Shopping Cart Settings", {
	onload: function(frm) {
		if(frm.doc.__onload && frm.doc.__onload.quotation_series) {
			frm.fields_dict.quotation_series.df.options = frm.doc.__onload.quotation_series;
			frm.refresh_field("quotation_series");
		}
	},
	refresh: function(frm) {
		toggle_mandatory(frm)
	},
	enable_checkout: function(frm) {
		toggle_mandatory(frm)
	},
	enabled: function(frm) {
		console.log("cool")
		if (frm.doc.enabled === 1) {
			frm.doc.enable_variants = 1;
			frm.refresh_field('enable_variants');
		}
	}
});

function toggle_mandatory (frm) {
	frm.toggle_reqd("payment_gateway_account", false);
	if(frm.doc.enabled && frm.doc.enable_checkout) {
		frm.toggle_reqd("payment_gateway_account", true);
	}
}
