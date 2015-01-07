frappe.listview_settings['Purchase Order'] = {
	add_fields: ["grand_total", "company", "currency", "supplier",
		"supplier_name", "per_received", "per_billed", "status"],
	get_indicator: function(doc) {
        if(doc.status==="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if(doc.per_received < 100 && doc.status!=="Stopped") {
			return [__("Not Received"), "orange", "per_received,<,100|status,!=,Stopped"];
		} else if(doc.per_received == 100 && doc.per_billed < 100 && doc.status!=="Stopped") {
			return [__("To Bill"), "orange", "per_received,=,100|per_billed,<,100|status,!=,Stopped"];
		} else if(doc.per_received == 100 && doc.per_billed == 100 && doc.status!=="Stopped") {
			return [__("Completed"), "green", "per_received,=,100|per_billed,=,100|status,!=,Stopped"];
		}
	}
};
