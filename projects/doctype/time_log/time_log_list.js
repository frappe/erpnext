// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
wn.listview_settings['Time Log'] = {
	add_fields: ["`tabTime Log`.`status`", "`tabTime Log`.`billable`", "`tabTime Log`.`activity_type`"],
	selectable: true,
	onload: function(me) {
		me.appframe.add_button(wn._("Make Time Log Batch"), function() {
			var selected = me.get_checked_items() || [];

			if(!selected.length) {
				msgprint(wn._("Please select Time Logs."))
			}
			
			// select only billable time logs
			for(var i in selected) {
				var d = selected[i];
				if(!d.billable) {
					msgprint(wn._("Time Log is not billable") + ": " + d.name);
					return;
				}
				if(d.status!="Submitted") {
					msgprint(wn._("Time Log Status must be Submitted."));
				}
			}
			
			// make batch
			wn.model.with_doctype("Time Log Batch", function() {
				var tlb = wn.model.get_new_doc("Time Log Batch");
				$.each(selected, function(i, d) {
					var detail = wn.model.get_new_doc("Time Log Batch Detail");
					$.extend(detail, {
						"parenttype": "Time Log Batch",
						"parentfield": "time_log_batch_details",
						"parent": tlb.name,
						"time_log": d.name,
						"activity_type": d.activity_type,
						"created_by": d.owner,
						"idx": i+1
					});
				})
				wn.set_route("Form", "Time Log Batch", tlb.name);
			})
			
		}, "icon-file-alt");
	}
};
