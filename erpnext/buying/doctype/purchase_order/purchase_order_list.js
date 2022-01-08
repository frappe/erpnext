frappe.listview_settings['Purchase Order'] = {
	add_fields: [
		"supplier", "supplier_name",
		"base_grand_total", "company", "currency",
		"per_received", "per_billed", "per_completed", "status"
	],

	get_indicator: function (doc) {
		// Closed
		if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];

		// On Hold
		} else if (doc.status === "On Hold") {
			return [__("On Hold"), "orange", "status,=,On Hold"];

		// Delivered by Supplier
		} else if (doc.status === "Delivered") {
			return [__("Delivered"), "green", "status,=,Closed"];

		// Completed
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];

		// To Receive
		} else if (flt(doc.per_received, 6) < 100) {
			// Not Received and Not Billed
			if (flt(doc.per_completed, 6) < 100) {
				return [__("To Receive and Bill"), "orange",
					"per_received,<,100|per_completed,<,100|status,!=,Closed|docstatus,=,1"];

			// Billed but not received
			} else {
				return [__("To Receive"), "orange",
					"per_received,<,100|per_completed,=,100|status,!=,Closed|docstatus,=,1"];
			}

		// To Bill
		} else if (flt(doc.per_received, 6) >= 100 && flt(doc.per_completed, 6) < 100) {
			return [__("To Bill"), "orange",
				"per_received,=,100|per_completed,<,100|status,!=,Closed|docstatus,=,1"];
		}
	},

	onload: function (listview) {
		var method = "erpnext.buying.doctype.purchase_order.purchase_order.close_or_unclose_purchase_orders";

		listview.page.add_action_item(__("Close"), function () {
			listview.call_for_selected_items(method, { "status": "Closed" });
		});

		listview.page.add_action_item(__("Re-Open"), function () {
			listview.call_for_selected_items(method, { "status": "Submitted" });
		});
	}
};
