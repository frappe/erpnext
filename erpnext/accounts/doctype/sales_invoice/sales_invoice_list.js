// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Sales Invoice'] = {
	add_fields: ["customer", "customer_name", "base_grand_total", "outstanding_amount", "due_date", "company",
		"currency", "is_return"],
	get_indicator: function(doc) {
		const status_colors = {
			"Draft": "grey",
			"Unpaid": "orange",
			"Paid": "green",
			"Return": "gray",
			"Credit Note Issued": "gray",
			"Unpaid and Discounted": "orange",
			"Partly Paid and Discounted": "yellow",
			"Overdue and Discounted": "red",
			"Overdue": "red",
			"Partly Paid": "yellow",
			"Internal Transfer": "darkgrey"
		};
		return [__(doc.status), status_colors[doc.status], "status,=,"+doc.status];
	},
	right_column: "grand_total",

	onload: function(listview) {
		listview.page.add_action_item(__("Delivery Note"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Create {0} Delivery Note ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Delivery Note From Sales Invoice"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} delivery note`,count_of_rows);
				}
			})
		});

		listview.page.add_action_item(__("Payment"), ()=>{
			checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

			frappe.confirm(__("Make {0} Payment ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Payment From Sales Invoice"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} payment`,count_of_rows);
				}
			})
		});
	}
};
