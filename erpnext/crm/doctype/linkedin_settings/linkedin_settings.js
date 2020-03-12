// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('LinkedIn Settings', {
	login_button: function(frm){
		if(!(frm.doc.consumer_key && frm.doc.consumer_secret)){
			frappe.msgprint("Please set Consumer Key and Consumer Key Secret to Proceed");
			return;
		}
		frappe.call({
			doc: frm.doc,
			method: "get_authorization_url",
			callback : function(r) {
				window.location.href = r.message;
			}
		});
	}
});
