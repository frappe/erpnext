// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Goods Inward Note"] = {
	add_fields: ["status", "arrived_on"],
	get_indicator(doc) {
		const colors = {
			"In Custody": "orange",
			"Partially Received": "yellow",
			Received: "green",
			Returned: "red",
		};
		let label = __(doc.status);
		// goods waiting in custody wear their age, like quarantined lots
		if (["In Custody", "Partially Received"].includes(doc.status)) {
			const days = frappe.datetime.get_day_diff(frappe.datetime.now_date(), doc.arrived_on);
			if (days > 0) {
				label = __("{0} · {1}d", [label, days]);
			}
		}
		return [label, colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
