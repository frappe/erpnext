// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('LinkedIn Settings', {
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
		let msg,color = null;
		if(!frm.doc.person_urn){
			msg = "SignIn First With LinkedIn.";
			color = "yellow";
		}
		else{
			let d = new Date(frm.doc.modified)
			d.setDate(d.getDate()+60);
			let dn = new Date()
			let days = d.getTime() - dn.getTime();
			days = Math.floor(days/(1000 * 3600 * 24));
			if(days>0){
				msg = "Your Session will be expire in " + days + " days.";
			}
			else{
				msg = "Session is expired, SignIn with LinkedIn to continue.";
				color = "yellow";
			}
		}
		frm.dashboard.add_comment(msg, color, true);

		frm.add_custom_button(('SignIn With LinkedIn'), function(){
			if(!(frm.doc.consumer_key && frm.doc.consumer_secret)){
				frappe.msgprint(__("Please set Consumer Key and Consumer Key Secret to Proceed"));
				return;
			}
			frappe.call({
				doc: frm.doc,
				method: "get_authorization_url",
				callback : function(r) {
					window.location.href = r.message;
				}
			});
		}).removeClass("btn-xs").addClass("btn-primary");
	}
});
