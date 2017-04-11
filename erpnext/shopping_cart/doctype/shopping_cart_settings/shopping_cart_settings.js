// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__onload && cur_frm.doc.__onload.quotation_series) {
			cur_frm.fields_dict.quotation_series.df.options = cur_frm.doc.__onload.quotation_series;
		}
	},
	refresh: function(){
		toggle_mandatory(cur_frm)
	},
	enable_checkout: function(){
		toggle_mandatory(cur_frm)
	}
});


function toggle_mandatory (cur_frm){
	cur_frm.toggle_reqd("payment_gateway_account", false);
	if(cur_frm.doc.enabled && cur_frm.doc.enable_checkout) {
		cur_frm.toggle_reqd("payment_gateway_account", true);
	}
}
