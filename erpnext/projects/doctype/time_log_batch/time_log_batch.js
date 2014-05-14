// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("time_log", "activity_type", "activity_type");
cur_frm.add_fetch("time_log", "owner", "created_by");
cur_frm.add_fetch("time_log", "hours", "hours");

cur_frm.set_query("time_log", "time_log_batch_details", function(doc) {
	return {
		query: "erpnext.projects.utils.get_time_log_list",
		filters: {
			"billable": 1,
			"status": "Submitted"
		}
	}
});

$.extend(cur_frm.cscript, {
	refresh: function(doc) {
		cur_frm.set_intro({
			"Draft": __("Select Time Logs and Submit to create a new Sales Invoice."),
			"Submitted": __("Click on 'Make Sales Invoice' button to create a new Sales Invoice."),
			"Billed": __("This Time Log Batch has been billed."),
			"Cancelled": __("This Time Log Batch has been cancelled.")
		}[doc.status]);

		if(doc.status=="Submitted") {
			cur_frm.add_custom_button(__("Make Sales Invoice"), function() { cur_frm.cscript.make_invoice() },
				"icon-file-alt");
		}
	},
	make_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.projects.doctype.time_log_batch.time_log_batch.make_sales_invoice",
			frm: cur_frm
		});
	}
});
