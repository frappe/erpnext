frappe.listview_settings["Supplier Quotation"] = {
	add_fields: ["supplier", "base_grand_total", "status", "company", "currency"],
	get_indicator: function (doc) {
		if (doc.status === "Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if (doc.status === "Rejected") {
			return [__("Lost"), "gray", "status,=,Lost"];
		} else if (doc.status === "Expired") {
			return [__("Expired"), "gray", "status,=,Expired"];
		}
	},

	onload: function (listview) {
<<<<<<< HEAD
		if (frappe.model.can_create("Purchase Order")) {
			listview.page.add_action_item(__("Purchase Order"), () => {
				erpnext.bulk_transaction_processing.create(listview, "Supplier Quotation", "Purchase Order");
			});
		}

		if (frappe.model.can_create("Purchase Invoice")) {
			listview.page.add_action_item(__("Purchase Invoice"), () => {
				erpnext.bulk_transaction_processing.create(
					listview,
					"Supplier Quotation",
					"Purchase Invoice"
				);
			});
		}
=======
		listview.page.add_action_item(__("Purchase Order"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Supplier Quotation", "Purchase Order");
		});

		listview.page.add_action_item(__("Purchase Invoice"), () => {
			erpnext.bulk_transaction_processing.create(listview, "Supplier Quotation", "Purchase Invoice");
		});
>>>>>>> 7c4cf3e834 (Favicon.svg)
	},
};
