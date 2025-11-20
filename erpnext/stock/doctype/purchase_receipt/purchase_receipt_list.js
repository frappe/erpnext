frappe.listview_settings["Purchase Receipt"] = {
	add_fields: [
		"supplier",
		"supplier_name",
		"base_grand_total",
		"is_subcontracted",
		"transporter_name",
		"is_return",
		"status",
		"per_billed",
		"currency",
	],
	get_indicator: function (doc) {
		if (cint(doc.is_return) == 1 && doc.status == "Return") {
			return [__("Return"), "gray", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.per_returned, 2) === 100) {
			return [__("Return Issued"), "grey", "per_returned,=,100|docstatus,=,1"];
		} else if (flt(doc.grand_total || doc.base_grand_total) !== 0 && flt(doc.per_billed, 2) == 0) {
			return [__("To Bill"), "orange", "per_billed,<,100|docstatus,=,1"];
		} else if (flt(doc.per_billed, 2) > 0 && flt(doc.per_billed, 2) < 100) {
			return [__("Partly Billed"), "yellow", "per_billed,<,100|docstatus,=,1"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_billed, 2) >= 100) {
			return [__("Completed"), "green", "per_billed,>=,100|docstatus,=,1"];
		}
	},

	onload: function (listview) {
		listview.page.add_action_item(__("Purchase Invoice"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Purchase Receipt", "Purchase Invoice");
		});
	},
};
