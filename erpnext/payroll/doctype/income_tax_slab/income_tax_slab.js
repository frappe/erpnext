// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Income Tax Slab', {
	currency: function(frm) {
		frm.refresh_fields();
	},

	effective_from: function(frm){
		frappe.call({
			method:"erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.effective_from
			},
			callback: function(resp){
				if(resp.message){
					cur_frm.set_value("effective_from_nepali",resp.message)
				}
			}
		})
	},
});
