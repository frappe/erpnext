frappe.listview_settings['Subscription'] = {
	add_fields: ["next_schedule_date"],
	get_indicator: function(doc) {
		if(doc.next_schedule_date >= frappe.datetime.get_today() ) {
			return [__("Active"), "green"];
		} else if(doc.docstatus === 0) {
			return [__("Draft"), "red", "docstatus,=,0"];
		} else {
			return [__("Expired"), "darkgrey"];
		}
	}
};