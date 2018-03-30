frappe.listview_settings['Payment Request'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Draft") {
			return [__("Draft"), "darkgrey", "status,=,Draft"];
		}
		else if(doc.status == "Initiated") {
			return [__("Initiated"), "green", "status,=,Initiated"];
		}
		else if(doc.status == "Paid") {
			return [__("Paid"), "blue", "status,=,Paid"];
		}
		else if(doc.status == "Cancelled") {
			return [__("Cancelled"), "orange", "status,=,Cancelled"];
		}
	}	
}
