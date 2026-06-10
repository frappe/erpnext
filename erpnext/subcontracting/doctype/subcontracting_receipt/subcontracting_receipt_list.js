// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Subcontracting Receipt"] = {
	add_fields: ["quality_status"],
	get_indicator: function (doc) {
		const quality = erpnext.utils.get_quality_indicator(doc);
		if (quality) return quality;
		const status_colors = {
			Draft: "red",
			Return: "gray",
			"Return Issued": "grey",
			Completed: "green",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
};
