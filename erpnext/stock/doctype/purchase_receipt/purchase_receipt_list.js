frappe.listview_settings['Purchase Receipt'] = {
	add_fields: ["supplier", "supplier_name", "base_grand_total", "is_subcontracted",
		"transporter_name", "is_return", "status", "per_billed", "per_completed", "currency"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.grand_total) !== 0 && flt(doc.per_completed, 2) < 100) {
			return [__("To Bill"), "orange", "per_completed,<,100"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_completed, 2) == 100) {
			return [__("Completed"), "green", "per_completed,=,100"];
		}
	}
};
