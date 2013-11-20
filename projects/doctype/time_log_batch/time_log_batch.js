// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("time_log", "activity_type", "activity_type");
cur_frm.add_fetch("time_log", "owner", "created_by");
cur_frm.add_fetch("time_log", "hours", "hours");

cur_frm.set_query("time_log", "time_log_batch_details", function(doc) {
	return {
		query: "projects.utils.get_time_log_list",
		filters: {
			"billable": 1,
			"status": "Submitted"
		}
	}
});

$.extend(cur_frm.cscript, {
	refresh: function(doc) {
		cur_frm.set_intro({
			"Draft": wn._("Select Time Logs and Submit to create a new Sales Invoice."),
			"Submitted": wn._("Click on 'Make Sales Invoice' button to create a new Sales Invoice."),
			"Billed": wn._("This Time Log Batch has been billed."),
			"Cancelled": wn._("This Time Log Batch has been cancelled.")
		}[doc.status]);
		
		if(doc.status=="Submitted") {
			cur_frm.add_custom_button(wn._("Make Sales Invoice"), function() { cur_frm.cscript.make_invoice() }, 
				"icon-file-alt");
		}
	},
	make_invoice: function() {
		var doc = cur_frm.doc;
		wn.model.map({
			source: wn.model.get_doclist(doc.doctype, doc.name),
			target: "Sales Invoice"
		});
	}
});