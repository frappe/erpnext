frappe.listview_settings['Quality Action'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		}
		else{
			return [__("Open"), "red", "status,=,Open"];
		}
	}
};