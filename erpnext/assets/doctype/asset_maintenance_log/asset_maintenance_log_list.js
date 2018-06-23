frappe.listview_settings['Asset Maintenance Log'] = {
	add_fields: ["maintenance_status"],
	get_indicator: function(doc) {
		if(doc.maintenance_status=="Pending") {
			return [__("Pending"), "orange"];
		} else if(doc.maintenance_status=="Completed") {
			return [__("Completed"), "green"];
		} else if(doc.maintenance_status=="Cancelled") {
			return [__("Cancelled"), "red"];
		} else if(doc.maintenance_status=="Overdue") {
			return [__("Overdue"), "red"];
		}
	}
};
