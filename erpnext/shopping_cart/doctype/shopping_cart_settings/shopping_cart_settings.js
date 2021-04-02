// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Shopping Cart Settings", {
	onload: function(frm) {
		if(frm.doc.__onload && frm.doc.__onload.quotation_series) {
			frm.fields_dict.quotation_series.df.options = frm.doc.__onload.quotation_series;
			frm.refresh_field("quotation_series");
		}
	},
	refresh: function(frm){
		toggle_mandatory(frm)
	},
	enable_checkout: function(frm){
		toggle_mandatory(frm)
	},
	enabled: function(frm) {
		if (frm.doc.enabled === 1) {
			frm.set_value('enable_variants', 1);
		}
		let is_required = frm.doc.enabled ? 1 : 0;
		frm.toggle_reqd(["company", "default_customer_group", "quotation_series"], is_required);
	}
});


function toggle_mandatory (frm){
	frm.toggle_reqd("payment_gateway_account", false);
	if(frm.doc.enabled && frm.doc.enable_checkout) {
		frm.toggle_reqd("payment_gateway_account", true);
	}
}
