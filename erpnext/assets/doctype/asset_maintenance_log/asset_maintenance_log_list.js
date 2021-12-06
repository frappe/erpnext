frappe.listview_settings['Asset Maintenance Log'] = {
	add_fields: ["maintenance_status"],
	has_indicator_for_draft: 1,
	get_indicator: function(doc) {
		if (doc.maintenance_status=="Planned") {
			return [__(doc.maintenance_status), "orange", "status,=," + doc.maintenance_status];
		} else if (doc.maintenance_status=="Completed") {
			return [__(doc.maintenance_status), "green", "status,=," + doc.maintenance_status];
		} else if (doc.maintenance_status=="Cancelled") {
			return [__(doc.maintenance_status), "red", "status,=," + doc.maintenance_status];
		} else if (doc.maintenance_status=="Overdue") {
			return [__(doc.maintenance_status), "red", "status,=," + doc.maintenance_status];
		}
	}
};
