// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Time Log'] = {
	add_fields: ["status", "billable", "activity_type", "task", "project", "hours"],
	selectable: true,
	onload: function(me) {
		me.appframe.add_primary_action(__("Make Time Log Batch"), function() {
			var selected = me.get_checked_items() || [];

			if(!selected.length) {
				msgprint(__("Please select Time Logs."));
				return;
			}

			// select only billable time logs
			for(var i in selected) {
				var d = selected[i];
				if(!d.billable) {
					msgprint(__("Time Log is not billable") + ": " + d.name);
					return;
				}
				if(d.status!="Submitted") {
					msgprint(__("Time Log Status must be Submitted."));
					return
				}
			}

			// make batch
			frappe.model.with_doctype("Time Log Batch", function() {
				var tlb = frappe.model.get_new_doc("Time Log Batch");
				$.each(selected, function(i, d) {
					var detail = frappe.model.get_new_doc("Time Log Batch Detail", tlb,
						"time_log_batch_details");

					$.extend(detail, {
						"time_log": d.name,
						"activity_type": d.activity_type,
						"created_by": d.owner,
						"hours": d.hours
					});
				})
				frappe.set_route("Form", "Time Log Batch", tlb.name);
			})

		}, "icon-file-alt");
	}
};
