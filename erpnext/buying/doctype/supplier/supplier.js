// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Supplier", {
	refresh: function(frm) {
		if(frappe.defaults.get_default("supp_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		if(frm.doc.__islocal){
	    	hide_field(['address_html','contact_html']);
			erpnext.utils.clear_address_and_contact(frm);
		}
		else {
		  	unhide_field(['address_html','contact_html']);
			erpnext.utils.render_address_and_contact(frm);
		}
	},
});

cur_frm.fields_dict['default_price_list'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'buying': 1}
	}
}

cur_frm.fields_dict['accounts'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		filters: {
			'account_type': 'Payable',
			'company': d.company,
			"is_group": 0
		}
	}
}
