frappe.listview_settings['Loan'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Sanctioned") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		} else if (doc.status == "Disbursed") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "Repaid/Closed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	}
};
