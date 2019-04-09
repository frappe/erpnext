frappe.listview_settings['Batch'] = {
	add_fields: ["item", "expiry_date", "batch_qty"],
	get_indicator: function (doc) {
		if (!doc.batch_qty) {
			return ["Empty", "darkgrey", "batch_qty,=,0"];
		} else {
			if (doc.expiry_date) {
				if (frappe.datetime.get_diff(doc.expiry_date, frappe.datetime.nowdate()) <= 0) {
					return [__("Expired"), "red", "expiry_date,>=,Today|batch_qty,>,0"]
				} else {
					return [__("Not Expired"), "green", "expiry_date,<,Today|batch_qty,>,0"]
				}
			} else {
				return ["Active", "green", "batch_qty,>,0"];
			};
		};
	}
};
