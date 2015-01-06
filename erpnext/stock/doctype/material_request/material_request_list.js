frappe.listview_settings['Material Request'] = {
	add_fields: ["material_request_type", "status", "per_ordered"],
	filters: [["per_ordered", "<", 100]],
	get_status: function(doc) {
		if(doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} if(doc.docstatus==1 && doc.per_ordered < 100) {
			return [__("Pending"), "orange", "per_ordered,<,100"];
		} else if(doc.status==1 && doc.per_ordered == 100) {
			return [__("Completed"), "green", "per_ordered,=,100"];
		}
	}
};
