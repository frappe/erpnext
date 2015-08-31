frappe.listview_settings['Batch'] = {
	add_fields: ["item", "expiry_date"],
	get_indicator: function(doc) {
		if(doc.expiry_date && frappe.datetime.get_diff(doc.expiry_date) <= 0) {
			return [__("Expired"), "red", "expiry_date,>=,Today"]
		} else if(doc.expiry_date) {
			return [__("Not Expired"), "green", "expiry_date,<,Today"]
		} else {
			return ["Not Set", "darkgrey", ""];
		}
	}
};
