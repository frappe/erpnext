frappe.listview_settings['Quality Review'] = {
	add_fields: ["status"],
	get_indicator: function(doc)
	{
		if(doc.status == "Closed") {
			return [__("Closed"), "green", "action,=,Closed"];
		}
		else if(doc.status == "Open") {
			return [__("Open"), "red", "action,=,Open"];
		}
	}
};