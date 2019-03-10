frappe.listview_settings['Employee Advance'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Claimed") {
			return [__("Claimed"), "green", "status,=,Claimed"];
		} else if(doc.status == "Unclaimed") {
			return [__("Unclaimed"), "orange", "status,=,Unclaimed"];
		} else if(doc.status == "Unpaid") {
			return [__("Unpaid"), "red", "status,=,Unpaid"];
		}
	}
};
