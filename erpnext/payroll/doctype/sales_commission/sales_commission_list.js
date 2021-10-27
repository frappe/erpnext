frappe.listview_settings['Sales Commission'] = {
	add_fields: ["total_commission_amount", "status"],
	get_indicator: function (doc) {
		if (doc.status == "Paid") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}  else {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	}
};