// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Action', {
	onload: function(frm) {
		frm.set_value("date", frappe.datetime.get_today());
		frm.refresh();
	},
	document_name: function(frm){
		frm.call("get_document", {
			"document_type": frm.doc.document_type,
			"document_name": frm.doc.document_name
		}, () => {
			frm.refresh();
		});
	},
});