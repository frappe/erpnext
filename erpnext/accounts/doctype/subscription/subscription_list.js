frappe.listview_settings['Subscription'] = {
	add_fields: ["next_schedule_date"],
	get_indicator: function(doc) {
		if(doc.disabled) {
			return [__("Disabled"), "red"];
		} else if(doc.next_schedule_date >= frappe.datetime.get_today() && doc.status != 'Stopped') {
			return [__("Active"), "green"];
		} else if(doc.docstatus === 0) {
			return [__("Draft"), "red", "docstatus,=,0"];
		} else if(doc.status === 'Stopped') {
			return [__("Stopped"), "red"];
		} else {
			return [__("Expired"), "darkgrey"];
		}
	}
};