// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fuel Price', {
	refresh: function(frm) {
	},
	setup:function(frm){
		frm.set_query("item_code",function(){
			return {
				filters:{disabled:0,
				is_pol_item:1}
			}
		})
	}
});
