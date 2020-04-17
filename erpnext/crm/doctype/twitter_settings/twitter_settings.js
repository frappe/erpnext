// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Twitter Settings', {
	onload: function(frm){
		if(frm.doc.session_status == 'Expired' && frm.doc.consumer_key && frm.doc.consumer_secret){
			frappe.confirm(
				__('Session not valid, Do you want to login?'),
				function(){
					frm.trigger("login");
				},
				function(){
					window.close();
				}
			)
		}
	},
	refresh: function(frm){
		if(frm.doc.session_status=="Active"){
			frm.dashboard.set_headline_alert(
				'<div class="row">' +
					'<div class="col-xs-12">' +
						'<span class="indicator whitespace-nowrap green"><span class="hidden-xs">'+ __("Session Active") +'</span></span> ' +
					'</div>' +
				'</div>'
			);
		}
		else if(frm.doc.session_status=="Expired"){
			frm.dashboard.set_headline_alert(
				'<div class="row">' +
					'<div class="col-xs-12">' +
						'<span class="indicator whitespace-nowrap red"><span class="hidden-xs">'+ __("Session Not Active. Save doc to login.") +'</span></span> ' +
					'</div>' +
				'</div>'
			);
		}
	},
	login: function(frm){
		if(frm.doc.consumer_key && frm.doc.consumer_secret){
			frappe.call({
				doc: frm.doc,
				method: "get_authorize_url",
				callback : function(r) {
					window.location.href = r.message;
				}
			});
		}
	},
	after_save: function(frm){
		frm.trigger("login");
	}
});
