frappe.listview_settings['Sales Commission'] = {
    get_indicator: function (doc) {
		if (doc.status == "Paid") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}  else {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	}
}