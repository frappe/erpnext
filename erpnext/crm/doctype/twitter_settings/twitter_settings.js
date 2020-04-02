// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Twitter Settings', {
	onload: function(frm){
		let url = window.location.href
		let hashes = (url.split("?")[1])
		if(hashes){
			let hash = hashes.split("=")
			if(hash[0] == "status"){
				if(hash[1] == 1){
					frappe.msgprint(__("Login Success"))
				}
			}
		}
	},
	refresh: function(frm){
		frm.add_custom_button(('Sign In With Twitter'), function(){
			if(!(frm.doc.consumer_key && frm.doc.consumer_secret)){
				frappe.msgprint(__("Please set Consumer Key and Consumer Key Secret to Proceed"));
				return;
			}
			frappe.call({
				doc: frm.doc,
				method: "get_authorize_url",
				callback : function(r) {
					window.location.href = r.message;
				}
			});
		}).removeClass("btn-xs").addClass("btn-primary");
	}
});
