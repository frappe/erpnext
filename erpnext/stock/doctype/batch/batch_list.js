frappe.listview_settings['Batch'] = {
	add_fields: ["item", "expiry_date", "batch_qty", "disabled"],
	get_indicator: (doc) => {
		if (doc.disabled) {
			return [__("Disabled"), "gray", "disabled,=,1"];
		} else if (!doc.batch_qty) {
			return [__("Empty"), "gray", "batch_qty,=,0|disabled,=,0"];
		} else if (doc.expiry_date && frappe.datetime.get_diff(doc.expiry_date, frappe.datetime.nowdate()) <= 0) {
			return [__("Expired"), "red", "expiry_date,not in,|expiry_date,<=,Today|batch_qty,>,0|disabled,=,0"]
		} else {
			return [__("Active"), "green", "batch_qty,>,0|disabled,=,0"];
		};
	}
};
