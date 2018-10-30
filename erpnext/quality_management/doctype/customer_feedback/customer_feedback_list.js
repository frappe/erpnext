frappe.listview_settings['Customer Feedback'] = {
	add_fields: ["action"],
	get_indicator: function(doc) {
		if(doc.action == "No Action") {
			return [__("No Action"), "green", "action,=,No Action"];
		}
		else if(doc.action == "Action Initialised") {
			return [__("Action Initialised"), "red", "action,=,Action Initialised"];
		}	
	}	
};