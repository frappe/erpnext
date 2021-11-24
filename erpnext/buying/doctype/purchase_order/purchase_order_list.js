frappe.listview_settings['Purchase Order'] = {
	add_fields: ["base_grand_total", "company", "currency", "supplier",
		"supplier_name", "per_received", "per_billed", "status"],
	get_indicator: function (doc) {
		if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "On Hold") {
			return [__("On Hold"), "orange", "status,=,On Hold"];
		} else if (doc.status === "Delivered") {
			return [__("Delivered"), "green", "status,=,Closed"];
		} else if (flt(doc.per_received, 2) < 100 && doc.status !== "Closed") {
			if (flt(doc.per_billed, 2) < 100) {
				return [__("To Receive and Bill"), "orange",
					"per_received,<,100|per_billed,<,100|status,!=,Closed"];
			} else {
				return [__("To Receive"), "orange",
					"per_received,<,100|per_billed,=,100|status,!=,Closed"];
			}
		} else if (flt(doc.per_received, 2) >= 100 && flt(doc.per_billed, 2) < 100 && doc.status !== "Closed") {
			return [__("To Bill"), "orange", "per_received,=,100|per_billed,<,100|status,!=,Closed"];
		} else if (flt(doc.per_received, 2) >= 100 && flt(doc.per_billed, 2) == 100 && doc.status !== "Closed") {
			return [__("Completed"), "green", "per_received,=,100|per_billed,=,100|status,!=,Closed"];
		}
	},
	onload: function (listview) {
		var method = "erpnext.buying.doctype.purchase_order.purchase_order.close_or_unclose_purchase_orders";

		listview.page.add_menu_item(__("Close"), function () {
			listview.call_for_selected_items(method, { "status": "Closed" });
		});

		listview.page.add_menu_item(__("Reopen"), function () {
			listview.call_for_selected_items(method, { "status": "Submitted" });
		});


		listview.page.add_action_item(__("Purchase Invoice"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Purchase Invoice ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Purchase Invoice From Purchase Order"}
					}).then(r => {
						console.log(r);
						frappe.show_alert("Purchase Invoice Created Successfully !",5);
					})
			})
		});

		listview.page.add_action_item(__("Purchase Receipt"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Purchase Receipt ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Purchase Receipt From Purchase Order"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} purchase receipt`,count_of_rows);
				}
			})
		});

		listview.page.add_action_item(__("Advance Payment"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Make {0} Advance Payment ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Advance Payment From Purchase Order"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} advance payment`,count_of_rows);
				}
			})
		});

	}
};
