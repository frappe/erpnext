cur_frm.add_fetch("time_log", "activity_type", "activity_type");
cur_frm.add_fetch("time_log", "owner", "created_by");

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
	refresh: function() {
		
	}
})