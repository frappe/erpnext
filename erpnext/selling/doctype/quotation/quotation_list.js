frappe.listview_settings['Quotation'] = {
	add_fields: ["customer_name", "base_grand_total", "status",
		"company", "currency", 'valid_till'],

	onload: function(listview) {
		if (listview.page.fields_dict.quotation_to) {
			listview.page.fields_dict.quotation_to.get_query = function() {
				return {
					"filters": {
						"name": ["in", ["Customer", "Lead"]],
					}
				};
			};
		}

		listview.page.add_action_item(__("Sales Order"),()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Sales Order ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Sales Order From Quotation"}
				}).then(r => {
					console.log(r);
				})
				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background to create ${count_of_rows} sales order`,count_of_rows);
				}
			})
		});

		listview.page.add_action_item(__("Sales Invoice"),()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Sales Invoice ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Sales Invoice From Quotation"}
				}).then(r => {
					console.log(r);
				})
			if(count_of_rows > 10){
				frappe.show_alert(`Starting a background to create ${count_of_rows} sales invoice`,count_of_rows);
			}

			})
		});
	},

	get_indicator: function(doc) {
		if(doc.status==="Open") {
			return [__("Open"), "orange", "status,=,Open"];
		} else if(doc.status==="Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if(doc.status==="Lost") {
			return [__("Lost"), "gray", "status,=,Lost"];
		} else if(doc.status==="Expired") {
			return [__("Expired"), "gray", "status,=,Expired"];
		}
	}
};
