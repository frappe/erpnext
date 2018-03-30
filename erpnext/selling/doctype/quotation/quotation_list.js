frappe.listview_settings['Quotation'] = {
	add_fields: ["customer_name", "base_grand_total", "status",
		"company", "currency", 'valid_till'],
	get_indicator: function(doc) {
		if(doc.status==="Submitted") {
			if (doc.valid_till && doc.valid_till < frappe.datetime.nowdate()) {
				return [__("Expired"), "darkgrey", "valid_till,<," + frappe.datetime.nowdate()];
			} else {
				return [__("Submitted"), "blue", "status,=,Submitted"];
			}
		} else if(doc.status==="Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if(doc.status==="Lost") {
			return [__("Lost"), "darkgrey", "status,=,Lost"];
		}
	}
};
