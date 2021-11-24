frappe.listview_settings['Sales Order'] = {
	add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date",
		"per_delivered", "per_billed", "status", "order_type", "name", "skip_delivery_note"],
	get_indicator: function (doc) {
		if (doc.status === "Closed") {
			// Closed
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "On Hold") {
			// on hold
			return [__("On Hold"), "orange", "status,=,On Hold"];
		} else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		} else if (!doc.skip_delivery_note && flt(doc.per_delivered, 6) < 100) {
			if (frappe.datetime.get_diff(doc.delivery_date) < 0) {
			// not delivered & overdue
				return [__("Overdue"), "red",
					"per_delivered,<,100|delivery_date,<,Today|status,!=,Closed"];
			} else if (flt(doc.grand_total) === 0) {
				// not delivered (zeroount order)
				return [__("To Deliver"), "orange",
					"per_delivered,<,100|grand_total,=,0|status,!=,Closed"];
			} else if (flt(doc.per_billed, 6) < 100) {
				// not delivered & not billed
				return [__("To Deliver and Bill"), "orange",
					"per_delivered,<,100|per_billed,<,100|status,!=,Closed"];
			} else {
				// not billed
				return [__("To Deliver"), "orange",
					"per_delivered,<,100|per_billed,=,100|status,!=,Closed"];
			}
		} else if ((flt(doc.per_delivered, 6) === 100) && flt(doc.grand_total) !== 0
			&& flt(doc.per_billed, 6) < 100) {
			// to bill
			return [__("To Bill"), "orange",
				"per_delivered,=,100|per_billed,<,100|status,!=,Closed"];
		} else if (doc.skip_delivery_note && flt(doc.per_billed, 6) < 100){
			return [__("To Bill"), "orange", "per_billed,<,100|status,!=,Closed"];
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

		listview.page.add_action_item(__("Sales Invoice"),()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;
			frappe.confirm(__("Create {0} Sales Invoice ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Sales Invoice From Sales Order"}
				}).then(r => {
					console.log(r);
				})
				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background to create ${count_of_rows} sales invoice`,count_of_rows);
				}
			})
		});

		listview.page.add_action_item(__("Delivery Note"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;
			frappe.confirm(__("Create {0} Delivery Note ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Delivery Note From Sales Order"}
					}).then(r => {
						console.log(r);
					})
				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background to create ${count_of_rows} delivery note`,count_of_rows);
				}
			})
		})

		listview.page.add_action_item(__("Advance Payment"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;
			frappe.confirm(__("Create {0} Advance Payment ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Advance Payment From Sales Order"}
				}).then(r => {
					console.log(r);
				})
				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background to create ${count_of_rows} Advance Payment`,count_of_rows);
				}
			})
		})

	}
};
