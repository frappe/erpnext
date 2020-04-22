// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Affirm Settings', {
	is_sandbox: function(frm) {
		frm.toggle_reqd("public_sandbox_api_key", frm.doc.is_sandbox);
		frm.toggle_reqd("private_sandbox_api_key", frm.doc.is_sandbox);
		frm.toggle_reqd("public_api_key", !frm.doc.is_sandbox);
		frm.toggle_reqd("private_api_key", !frm.doc.is_sandbox);
	}
});
