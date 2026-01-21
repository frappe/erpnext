frappe.listview_settings["Sales Order"] = {
	add_fields: [
		"base_grand_total",
		"customer_name",
		"currency",
		"delivery_date",
		"per_delivered",
		"per_billed",
		"status",
		"advance_payment_status",
		"order_type",
		"name",
		"skip_delivery_note",
	],
	get_indicator: function (doc) {
		const color_map = {
			Closed: "green",
			"On Hold": "orange",
			Completed: "green",
			"To Pay": "gray",
			"To Bill": "orange",
			"To Deliver": "orange",
			"To Deliver and Bill": "orange",
			Cancelled: "red",
		};

		if (!doc.skip_delivery_note && flt(doc.per_delivered) < 100) {
			if (frappe.datetime.get_diff(doc.delivery_date) < 0) {
				// not delivered & overdue
				return [
					__("Overdue"),
					"red",
					"per_delivered,<,100|delivery_date,<,Today|status,!=,Closed|docstatus,=,1",
				];
			}
		}

		if (doc.status in color_map) {
			return [__(doc.status), color_map[doc.status]];
		}
	},
	onload: function (listview) {
		var method = "erpnext.selling.doctype.sales_order.sales_order.close_or_unclose_sales_orders";

		listview.page.add_action_item(__("Close"), function () {
			listview.call_for_selected_items(method, { status: "Closed" });
		});

		listview.page.add_action_item(__("Re-open"), function () {
			listview.call_for_selected_items(method, { status: "Submitted" });
		});

		if (frappe.model.can_create("Sales Invoice")) {
			listview.page.add_action_item(__("Sales Invoice"), () => {
				erpnext.bulk_transaction_processing.create(listview, "Sales Order", "Sales Invoice");
			});
		}

		if (frappe.model.can_create("Delivery Note")) {
			listview.page.add_action_item(__("Delivery Note"), () => {
				frappe.call({
					method: "erpnext.selling.doctype.sales_order.sales_order.is_enable_cutoff_date_on_bulk_delivery_note_creation",
					callback: (r) => {
						if (r.message) {
							var dialog = new frappe.ui.Dialog({
								title: __("Select Items up to Delivery Date"),
								fields: [
									{
										fieldtype: "Date",
										fieldname: "delivery_date",
										default: frappe.datetime.add_days(frappe.datetime.nowdate(), 1),
									},
								],
							});
							dialog.set_primary_action(__("Select"), function (values) {
								var until_delivery_date = values.delivery_date;
								erpnext.bulk_transaction_processing.create(
									listview,
									"Sales Order",
									"Delivery Note",
									{
										until_delivery_date,
									}
								);
								dialog.hide();
							});
							dialog.show();
						} else {
							erpnext.bulk_transaction_processing.create(
								listview,
								"Sales Order",
								"Delivery Note"
							);
						}
					},
				});
			});
		}

		if (frappe.model.can_create("Payment Entry")) {
			listview.page.add_action_item(__("Advance Payment"), () => {
				erpnext.bulk_transaction_processing.create(listview, "Sales Order", "Payment Entry");
			});
		}
	},
};
