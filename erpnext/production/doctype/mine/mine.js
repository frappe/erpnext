// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Mine', {
	onload: function (frm) {
		frm.set_query("village", function (doc) {
			return {
				filters: { 'is_village': 1 }
			};
		});
		frm.set_query("gewog", function (doc) {
			return {
				filters: { 'is_gewog': 1 }
			};
		});
		frm.set_query("dzongkhag", function (doc) {
			return {
				filters: { 'is_dzongkhag': 1 }
			};
		});
		frm.set_query("dungkhag", function (doc) {
			return {
				filters: { 'is_dungkhag': 1 }
			};
		});
	},
	lease_start_date: function(frm){
		if (frm.doc.lease_end_date){
			duration(frm);
		}
	},
	lease_end_date: function(frm){
		if (frm.doc.lease_start_date){
			duration(frm);
		}
	},
	ec_issue_date: function(frm){
		if (frm.doc.ec_expiry_date){
			ec_duration(frm);
		}
	},
	ec_expiry_date: function(frm){
		if (frm.doc.ec_issue_date){
			ec_duration(frm);
		}
	}
});

function duration(frm){
	frappe.call({
		method:"erpnext.production.doctype.mine.mine.lease_duration",
		args: {
			"lease_start_date": frm.doc.lease_start_date,
			"lease_end_date": frm.doc.lease_end_date
		},
		callback: function (r){
			console.log(r.message)
			frm.set_value("lease_duration", r.message)
			frm.refresh_field("lease_duration")
		}
	});
}
function ec_duration(frm){
	frappe.call({
		method:"erpnext.production.doctype.mine.mine.ec_duration",
		args: {
			"ec_issue_date": frm.doc.ec_issue_date,
			"ec_expiry_date": frm.doc.ec_expiry_date
		},
		callback: function (r){
			console.log(r.message)
			frm.set_value("ec_duration", r.message)
			frm.refresh_field("ec_duration")
		}
	});
}