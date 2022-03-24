frappe.listview_settings['Payment Request'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Draft") {
			return [__("Draft"), "gray", "status,=,Draft"];
		}
		if(doc.status == "Requested") {
			return [__("Requested"), "green", "status,=,Requested"];
		}
		else if(doc.status == "Initiated") {
			return [__("Initiated"), "green", "status,=,Initiated"];
		}
		else if(doc.status == "Partially Paid") {
			return [__("Partially Paid"), "orange", "status,=,Partially Paid"];
		}
		else if(doc.status == "Paid") {
			return [__("Paid"), "blue", "status,=,Paid"];
		}
		else if(doc.status == "Cancelled") {
			return [__("Cancelled"), "red", "status,=,Cancelled"];
		}
	}
}
