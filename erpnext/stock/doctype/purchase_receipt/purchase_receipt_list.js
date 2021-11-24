frappe.listview_settings['Purchase Receipt'] = {
	add_fields: ["supplier", "supplier_name", "base_grand_total", "is_subcontracted",
		"transporter_name", "is_return", "status", "per_billed", "currency"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "gray", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (flt(doc.per_returned, 2) === 100) {
			return [__("Return Issued"), "grey", "per_returned,=,100"];
		} else if (flt(doc.grand_total) !== 0 && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (flt(doc.grand_total) === 0 || flt(doc.per_billed, 2) === 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	},

	onload: function(listview){

	listview.page.add_action_item(__("Purchase Invoice"), ()=>{
		checked_items = listview.get_checked_items();
		count_of_rows = checked_items.length;

		frappe.confirm(__("Create {0} Purchase Invoice ?", [count_of_rows]),()=>{
			frappe.call({
			method:"erpnext.utilities.bulk_transaction.transaction_processing",
			args: {data: checked_items, to_create: "Purchase Invoice From Purchase Receipt"}
			}).then(r => {
			console.log(r);
			})

			if(count_of_rows > 10){
				frappe.show_alert(`Starting a background job to create ${count_of_rows} purchase invoice`,count_of_rows);
			}
		})
		});
	}

};
