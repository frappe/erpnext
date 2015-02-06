frappe.listview_settings['Sales Order'] = {
	add_fields: ["grand_total", "customer_name", "currency", "delivery_date", "per_delivered", "per_billed",
		"status"],
	get_indicator: function(doc) {
        if(doc.status==="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
        } else if(doc.per_delivered < 100 && frappe.datetime.get_diff(doc.delivery_date) < 0) {
			return [__("Overdue"), "red", "per_delivered,<,100|delivery_date,<,Today|status,!=,Stopped"];
		} else if(doc.per_delivered < 100 && doc.status!=="Stopped") {
			return [__("Not Delivered"), "orange", "per_delivered,<,100|status,!=,Stopped"];
		} else if(doc.per_delivered == 100 && doc.per_billed < 100 && doc.status!=="Stopped") {
			return [__("To Bill"), "orange", "per_delivered,=,100|per_billed,<,100|status,!=,Stopped"];
		} else if(doc.per_delivered == 100 && doc.per_billed == 100 && doc.status!=="Stopped") {
			return [__("Completed"), "green", "per_delivered,=,100|per_billed,=,100|status,!=,Stopped"];
		}
	}
};
