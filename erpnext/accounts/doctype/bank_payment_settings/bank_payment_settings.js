// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Payment Settings', {
	refresh: function(frm) {

	},
	but_test_connectivity: function(frm){
		if(cur_frm.is_dirty()){
			frm.save();
		}
		
		return frappe.call({
			method: "erpnext.integrations.bps.test_connectivity",
			args: {'bank': frm.doc.financial_institution},
			callback: function(a, b) {
				//cur_frm.refresh();
			},
			freeze: true,
			freeze_message: 'Connecting...'
		});
	}
});
