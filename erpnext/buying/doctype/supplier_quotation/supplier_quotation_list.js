frappe.listview_settings['Supplier Quotation'] = {
	add_fields: ["supplier", "base_grand_total", "status", "company", "currency"],
	get_indicator: function(doc) {
		if(doc.status==="Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if(doc.status==="Rejected") {
			return [__("Lost"), "gray", "status,=,Lost"];
		} else if(doc.status==="Expired") {
			return [__("Expired"), "gray", "status,=,Expired"];
		}
	},

	onload: function(listview){
		listview.page.add_action_item(__("Purchase Order"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Purchase Order ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Purchase Order From Supplier Quotation"}
				}).then(r => {
					console.log(r);
				})
				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} purchase order`,count_of_rows);
				}
			});
		});

		listview.page.add_action_item(__("Purchase Invoice"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Purchase Invoice ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Purchase Invoice From Supplier Quotation"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} purchase invoice`,count_of_rows);
				}
			});
		});
	}
};
