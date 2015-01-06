frappe.listview_settings['Lead'] = {
	add_fields: ["territory", "company_name", "status", "source"],
	get_indicator: function(doc) {
		var indicator = [__(doc.status), "darkgrey", "status,=," + doc.status];
		if(doc.status==="Open") indicator[1] = "red";
		if(doc.status==="Opportunity") indicator[1] = "green";
		return indicator;
	}
};
