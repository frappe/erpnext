// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__onload && cur_frm.doc.__onload.quotation_series) {
			cur_frm.fields_dict.quotation_series.df.options = cur_frm.doc.__onload.quotation_series;
			cur_frm.refresh_field("quotation_series");
		}
	},
	refresh: function(){
		toggle_mandatory(cur_frm)
	},
	enable_checkout: function(){
		toggle_mandatory(cur_frm)
	},
});

frappe.ui.form.on('Shopping Cart Payment Gateway', {
	payment_gateway_account: function (frm, cdt, cdn) {
		const row = frm.selected_doc || locals[cdt][cdn];

		if (row.payment_gateway_account) {
			frappe.db.get_value('Payment Gateway Account', row.payment_gateway_account, 'payment_gateway', (r) => {
				if (r && r.payment_gateway) {
					frappe.model.set_value(cdt, cdn, "payment_gateway", r.payment_gateway)
					frappe.model.set_value(cdt, cdn, "label", r.payment_gateway)
				}
			});
		}
	}
});

function toggle_mandatory (cur_frm){
	cur_frm.toggle_reqd("gateways", false);
	if(cur_frm.doc.enabled && cur_frm.doc.enable_checkout) {
		cur_frm.toggle_reqd("gateways", true);
	}
}
