frappe.listview_settings['Newsletter'] = {
	add_fields: ["subject", "email_sent"],
	get_indicator: function(doc) {
		if(doc.email_sent) {
			return [__("Sent"), "green", "email_sent,=,Yes"];
		} else {
			return [__("Not Sent"), "orange", "email_sent,=,No"];
		}
	}
};
