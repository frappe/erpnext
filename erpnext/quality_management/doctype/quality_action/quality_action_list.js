frappe.listview_settings['Quality Action'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Planned") {
			return [__("Planned"), "green", "status,=,Planned"];
		}
		else{
			return [__("Under Review"), "red", "status,=,Under Review"];
		}
	}
};