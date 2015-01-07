frappe.listview_settings['Opportunity'] = {
	add_fields: ["customer_name", "enquiry_type", "enquiry_from", "status"],
	get_indicator: function(doc) {
		var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		if(doc.status=="Quotation") {
			indicator[1] = "green";
		}
		return indicator;
	}
};
