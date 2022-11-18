frappe.listview_settings['Purchase Receipt'] = {
	add_fields: [
		"supplier", "supplier_name", "transporter_name",
		"base_grand_total", "currency",
		"is_subcontracted", "is_return",
		"status", "per_billed", "per_completed",
	],

	get_indicator: function(doc) {
		// Return
		if(cint(doc.is_return)) {
			return [__("Return"), "grey", "is_return,=,Yes"];

		// Closed
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];

		// To Bill
		} else if (flt(doc.per_completed, 6) < 100) {
			return [__("To Bill"), "orange",
				"per_completed,<,100|status,!=,Closed|docstatus,=,1"];

		// Completed
		} else if (flt(doc.per_completed, 6) == 100) {
			return [__("Completed"), "green",
				"per_completed,=,100|docstatus,=,1"];
		}
	}
};
