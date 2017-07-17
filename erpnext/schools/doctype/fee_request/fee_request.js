// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fee Request', {
	refresh: function(frm) {
		frm.disable_save();	
	},
	fee_structure: function(frm) {
		if (frm.doc.fee_structure) {
			frappe.call({
				method: "erpnext.schools.doctype.fee_request.fee_request.get_fee_structure",
				args: {
					"target_doc": frm.doc.name,
					"source_name": frm.doc.fee_structure
				},
				callback: function(r) {
					var doc = frappe.model.sync(r.message);
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				}
			});
		}
	}
});

frappe.ui.form.on("Fee Component", {
	refresh: function(frm) {
		frm.set_read_only();
	}
});
