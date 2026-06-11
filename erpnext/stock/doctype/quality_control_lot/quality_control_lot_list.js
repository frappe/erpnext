// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Quality Control Lot"] = {
	add_fields: ["status", "creation"],
	get_indicator(doc) {
		const colors = {
			"Under Inspection": "orange",
			"Awaiting Release": "yellow",
			"Partially Released": "yellow",
			Released: "green",
			Rejected: "red",
		};
		let label = __(doc.status);
		// an open lot wears its age: quarantined stock nobody decides is
		// working capital standing still
		if (["Under Inspection", "Awaiting Release", "Partially Released"].includes(doc.status)) {
			const days = frappe.datetime.get_day_diff(frappe.datetime.now_date(), doc.creation);
			if (days > 0) {
				label = __("{0} · {1}d", [label, days]);
			}
		}
		return [label, colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
