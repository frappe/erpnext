frappe.listview_settings["Purchase Order"] = {
	add_fields: [
		"base_grand_total",
		"company",
		"currency",
		"supplier",
		"supplier_name",
		"per_received",
		"per_billed",
		"status",
		"advance_payment_status",
	],
	get_indicator: function (doc) {
		if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "On Hold") {
			return [__("On Hold"), "orange", "status,=,On Hold"];
		} else if (doc.status === "Delivered") {
			return [__("Delivered"), "green", "status,=,Closed"];
		} else if (doc.advance_payment_status == "Initiated") {
			return [__("To Pay"), "gray", "advance_payment_status,=,Initiated"];
		} else if (flt(doc.per_received, 2) < 100 && doc.status !== "Closed") {
			if (flt(doc.per_billed, 2) < 100) {
				return [
					__("To Receive and Bill"),
					"orange",
					"per_received,<,100|per_billed,<,100|status,!=,Closed",
				];
			} else {
				return [__("To Receive"), "orange", "per_received,<,100|per_billed,=,100|status,!=,Closed"];
			}
		} else if (
			flt(doc.per_received, 2) >= 100 &&
			flt(doc.per_billed, 2) < 100 &&
			doc.status !== "Closed"
		) {
			return [__("To Bill"), "orange", "per_received,=,100|per_billed,<,100|status,!=,Closed"];
		} else if (
			flt(doc.per_received, 2) >= 100 &&
			flt(doc.per_billed, 2) == 100 &&
			doc.status !== "Closed"
		) {
			return [__("Completed"), "green", "per_received,=,100|per_billed,=,100|status,!=,Closed"];
		}
	},
	onload: function (listview) {
		var method = "erpnext.buying.doctype.purchase_order.purchase_order.close_or_unclose_purchase_orders";

		listview.page.add_menu_item(__("Close"), function () {
			listview.call_for_selected_items(method, { status: "Closed" });
		});

		listview.page.add_menu_item(__("Reopen"), function () {
			listview.call_for_selected_items(method, { status: "Submitted" });
		});

		listview.page.add_action_item(__("Purchase Invoice"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Purchase Order", "Purchase Invoice");
		});

		listview.page.add_action_item(__("Purchase Receipt"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Purchase Order", "Purchase Receipt");
		});

		listview.page.add_action_item(__("Advance Payment"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Purchase Order", "Payment Entry");
		});
	},
};
