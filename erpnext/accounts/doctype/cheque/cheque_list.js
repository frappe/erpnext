// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings["Cheque"] = {
	add_fields: ["status", "cheque_date"],
	// PDC and Cleared come from dates, so they are shown, not stored. The Cheque Book tab
	// and the Cheque form use this too. The list has no clearance date, so a cleared
	// cheque shows as Issued there.
	get_indicator(doc) {
		const today = frappe.datetime.get_today();
		if (doc.status === "Issued" && doc.clearance_date) {
			return [__("Cleared"), "green", "status,=,Issued"];
		}
		if (doc.status === "Issued" && doc.cheque_date > today) {
			return [__("PDC"), "orange", `status,=,Issued|cheque_date,>,${today}`];
		}
		const color = { Available: "blue", Issued: "green", Cancelled: "red" }[doc.status];
		return [__(doc.status), color, `status,=,${doc.status}`];
	},
};
