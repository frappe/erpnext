frappe.listview_settings['Sales Order'] = {
	add_fields: [
		"name", "customer_name", "currency", "delivery_date",
		"per_delivered", "per_billed", "per_completed",
		"status", "skip_delivery_note"
	],
	get_indicator: function (doc) {
		// Closed
		if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];

		// On Hold
		} else if (doc.status === "On Hold") {
			return [__("On Hold"), "orange", "status,=,On Hold"];

		// Completed
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];

		// Undelivered
		} else if (flt(doc.per_delivered, 6) < 100 && !doc.skip_delivery_note) {
			if (frappe.datetime.get_diff(doc.delivery_date) < 0) {
			// Overdue
				return [__("Overdue"), "red",
					"per_delivered,<,100|delivery_date,<,Today|status,!=,Closed|docstatus,=,1"];

			// Not Delivered & Not Billed
			} else if (flt(doc.per_completed, 6) < 100) {
				return [__("To Deliver and Bill"), "orange",
					"per_delivered,<,100|per_completed,<,100|status,!=,Closed|docstatus,=,1"];

			// Billed but not delivered
			} else {
				return [__("To Deliver"), "orange",
					"per_delivered,<,100|per_completed,=,100|status,!=,Closed|docstatus,=,1"];
			}

		// To Bill
		} else if (flt(doc.per_completed, 6) < 100 && (flt(doc.per_delivered, 6) === 100 || doc.skip_delivery_note)) {
			// No Delivery Required
			if (doc.skip_delivery_note) {
				return [__("To Bill"), "orange",
					"per_completed,<,100|status,!=,Closed|docstatus,=,1"];

			// Delivered but not billed
			} else {
				return [__("To Bill"), "orange",
					"per_delivered,=,100|per_completed,<,100|status,!=,Closed|docstatus,=,1"];
			}
		}
	},
	onload: function(listview) {
		var method = "erpnext.selling.doctype.sales_order.sales_order.close_or_unclose_sales_orders";

		listview.page.add_action_item(__("Close"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});

		listview.page.add_action_item(__("Re-Open"), function() {
			listview.call_for_selected_items(method, {"status": "Submitted"});
		});
	}
};
