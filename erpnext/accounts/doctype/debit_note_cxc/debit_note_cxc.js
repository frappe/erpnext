// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Multiple Taxes', "isv", function (frm, cdt, cdn){
	if(frm.doc.taxes) {
		debugger
		var tax = "";
		var base = 0;
		$.each(frm.doc.taxes, function(index, data){
			tax = index.isv
			base = index.base_isv
		})
		debugger
		frappe.call({
			method: "erpnext.accounts.doctype.debit_note_cxc.debit_note_cxc.get_taxes",
			args: {
				tax: tax,
				base: base
			},
			callback: function(r) {
					// var items = [];
					// frm.clear_table("items");

					// frm.refresh_field("items");
				}
		})
	}
});
