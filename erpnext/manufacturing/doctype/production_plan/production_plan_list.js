frappe.listview_settings['Production Plan'] = {
	add_fields: ["status"],
	filters: [["status", "!=", "Stopped"]],
	get_indicator: function(doc) {
		if(doc.status==="Submitted") {
			return [__("Not Started"), "orange", "status,=,Submitted"];
		} else {
			return [__(doc.status), {
				"Draft": "red",
				"In Process": "orange",
				"Completed": "green",
				"Material Requested": "darkgrey",
				"Cancelled": "darkgrey"
			}[doc.status], "status,=," + doc.status];
		}
	}
};
