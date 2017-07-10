frappe.listview_settings['Sales Order'] = {
	add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date", "per_delivered", "per_billed",
		"status", "order_type"],
	get_indicator: function(doc) {
		if(doc.status==="Closed"){
			return [__("Closed"), "green", "status,=,Closed"];

		} else if (doc.order_type !== "Maintenance"
			&& flt(doc.per_delivered, 2) < 100 && frappe.datetime.get_diff(doc.delivery_date) < 0) {
			// to bill & overdue
			return [__("Overdue"), "red", "per_delivered,<,100|delivery_date,<,Today|status,!=,Closed"];

		} else if (doc.order_type !== "Maintenance"
			&& flt(doc.per_delivered, 2) < 100 && doc.status!=="Closed") {
			// not delivered

			if(flt(doc.per_billed, 2) < 100) {
				// not delivered & not billed

				return [__("To Deliver and Bill"), "orange",
					"per_delivered,<,100|per_billed,<,100|status,!=,Closed"];
			} else {
				// not billed

				return [__("To Deliver"), "orange",
					"per_delivered,<,100|per_billed,=,100|status,!=,Closed"];
			}

		} else if ((doc.order_type === "Maintenance" || flt(doc.per_delivered, 2) == 100)
			&& flt(doc.per_billed, 2) < 100 && doc.status!=="Closed") {

			// to bill
			return [__("To Bill"), "orange", "per_delivered,=,100|per_billed,<,100|status,!=,Closed"];

		} else if((doc.order_type === "Maintenance" || flt(doc.per_delivered, 2) == 100)
			&& flt(doc.per_billed, 2) == 100 && doc.status!=="Closed") {

			return [__("Completed"), "green", "per_delivered,=,100|per_billed,=,100|status,!=,Closed"];
		}
	},
	onload: function(listview) {
		var method = "erpnext.selling.doctype.sales_order.sales_order.close_or_unclose_sales_orders";

		listview.page.add_menu_item(__("Close"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});

		listview.page.add_menu_item(__("Re-open"), function() {
			listview.call_for_selected_items(method, {"status": "Submitted"});
		});

	}
};
