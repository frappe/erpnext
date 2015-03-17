frappe.listview_settings['Purchase Order'] = {
	add_fields: ["base_grand_total", "company", "currency", "supplier",
		"supplier_name", "per_received", "per_billed", "status"],
	get_indicator: function(doc) {
        if(doc.status==="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if(flt(doc.per_received) < 100 && doc.status!=="Stopped") {
			return [__("Not Received"), "orange", "per_received,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_received) == 100 && flt(doc.per_billed) < 100 && doc.status!=="Stopped") {
			return [__("To Bill"), "orange", "per_received,=,100|per_billed,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_received) == 100 && flt(doc.per_billed) == 100 && doc.status!=="Stopped") {
			return [__("Completed"), "green", "per_received,=,100|per_billed,=,100|status,!=,Stopped"];
		}
	},
	order_by: "per_received asc, modified desc"
};
