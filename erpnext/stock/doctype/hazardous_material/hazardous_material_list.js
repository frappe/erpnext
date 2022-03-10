frappe.listview_settings['Hazardous Material'] = {
    get_indicator: function(doc) {
		var status_color = {
			"Draft": "red",
            "For Approval": "yellow",
            "Approved": "green",
            "Review": "yellow"
		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	}
};