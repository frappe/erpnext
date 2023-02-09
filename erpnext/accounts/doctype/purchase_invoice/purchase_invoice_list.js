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
			erpnext.bulk_transaction_processing.create(listview, "Purchase Invoice", "Purchase Receipt");
		});

		listview.page.add_action_item(__("Payment"), ()=>{
			erpnext.bulk_transaction_processing.create(listview, "Purchase Invoice", "Payment Entry");
		});
	}
};
