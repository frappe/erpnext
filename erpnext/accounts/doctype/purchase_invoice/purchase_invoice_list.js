// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings["Purchase Invoice"] = {
	add_fields: [
		"supplier",
		"supplier_name",
		"base_grand_total",
		"outstanding_amount",
		"due_date",
		"company",
		"currency",
		"is_return",
		"release_date",
		"on_hold",
		"represents_company",
		"is_internal_supplier",
	],
	get_indicator(doc) {
		if (doc.status == "Debit Note Issued") {
			return [__(doc.status), "darkgrey", "status,=," + doc.status];
		}

		if (
			flt(doc.outstanding_amount) > 0 &&
			doc.docstatus == 1 &&
			cint(doc.on_hold)
		) {
			if (!doc.release_date) {
				return [__("On Hold"), "darkgrey"];
			} else if (
				frappe.datetime.get_diff(
					doc.release_date,
					frappe.datetime.nowdate()
				) > 0
			) {
				return [__("Temporarily on Hold"), "darkgrey"];
			}
		}

		const status_colors = {
			"Unpaid": "orange",
			"Paid": "green",
			"Return": "gray",
			"Overdue": "red",
			"Partly Paid": "yellow",
			"Internal Transfer": "darkgrey",
		};

		if (status_colors[doc.status]) {
			return [
				__(doc.status),
				status_colors[doc.status],
				"status,=," + doc.status,
			];
		}
	},

	onload: function(listview) {
		listview.page.add_action_item(__("Purchase Receipt"), ()=>{
		    checked_items = listview.get_checked_items();
			count_of_rows = checked_items.length;

		    frappe.confirm(__("Create {0} Purchase Receipt ?", [count_of_rows]),()=>{
				frappe.call({
					method:"erpnext.utilities.bulk_transaction.transaction_processing",
					args: {data: checked_items, to_create: "Purchase Receipt From Purchase Invoice"}
				}).then(r => {
					console.log(r);
				})

				if(count_of_rows > 10){
					frappe.show_alert(`Starting a background job to create ${count_of_rows} purchase receipt`,count_of_rows);
				}
		    })
		});

		listview.page.add_action_item(__("Payment"), ()=>{
		    checked_items = listview.get_checked_items();
		    count_of_rows = checked_items.length;

			frappe.confirm(__("Make {0} Payment ?", [count_of_rows]),()=>{
		        frappe.call({
		        method:"erpnext.utilities.bulk_transaction.transaction_processing",
		        args: {data: checked_items, to_create: "Payment From Purchase Invoice"}
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
