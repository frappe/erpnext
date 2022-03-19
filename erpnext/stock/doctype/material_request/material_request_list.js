frappe.listview_settings['Material Request'] = {
	add_fields: ["material_request_type", "status", "per_ordered", "per_received"],
	get_indicator: function(doc) {
		if(doc.status == "Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];

		} else if(flt(doc.per_received, 2) == 100) {
			return [__("Received"), "green", "per_received,=,100|status,!=,Stopped"];

		} else if(flt(doc.per_received, 2) > 0) {
			return [__("Partially Received"), "yellow", "per_received,>,0|status,!=,Stopped"];

		} else if (flt(doc.per_ordered, 2) == 100) {
			return [__("Ordered"), "blue", "per_ordered,=,100|per_received,=,0|status,!=,Stopped"];

		}  else if(flt(doc.per_ordered, 2) > 0) {
			return [__("Partially Ordered"), "yellow", "per_ordered,>,0|per_received,=,0|status,!=,Stopped"];

		} else if(flt(doc.per_ordered, 2) == 0) {
			return [__("Pending"), "orange", "per_ordered,=,0|per_received,=,0|status,!=,Stopped"];

		}
	}
};
