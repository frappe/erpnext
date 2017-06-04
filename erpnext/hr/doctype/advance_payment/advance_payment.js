// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Advance Payment', {
	refresh: function(frm) {
		if((!frm.doc.__islocal) && (frm.doc.status=='Approved')&& (frm.doc.paid_status=='Pending') && (frm.doc.docstatus===1)){
			frm.add_custom_button(__('Paid'),
				function() {
					frm.set_value("paid_status","Paid")
					frm.refresh()
				}
			);
			frm.add_custom_button(__('Canceled'),
				function() {
					frm.set_value("paid_status","Canceled")
					frm.refresh()
				}
			);
		}
	},
	employee:function(frm){
		frappe.call({
				method: "get_base",
				doc:frm.doc,
				callback: function(r) {
					console.log(r.message);
					cur_frm.refresh_fields(["base","amount"])
				}
			})
	}
});
