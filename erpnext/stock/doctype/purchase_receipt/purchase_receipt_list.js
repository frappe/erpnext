frappe.listview_settings['Purchase Receipt'] = {
	add_fields: ["is_return", "grand_total", "status", "per_billed"],
	get_indicator: function (doc) {
		if (cint(doc.is_return) == 1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.grand_total) !== 0 && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_billed, 2) == 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	}
};
