frappe.listview_settings['Material Request'] = {
	add_fields: ["material_request_type", "status", "per_ordered"],
	get_indicator: function(doc) {
		if(doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if(doc.docstatus==1 && flt(doc.per_ordered) < 100) {
			return [__("Pending"), "orange", "per_ordered,<,100"];
		} else if(doc.docstatus==1 && flt(doc.per_ordered) == 100) {
			return [__("Ordered"), "green", "per_ordered,=,100"];
		}
	}
};
