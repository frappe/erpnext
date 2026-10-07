frappe.listview_settings["Delivery Note"] = {
	add_fields: [
		"customer",
		"customer_name",
		"base_grand_total",
		"per_installed",
		"per_billed",
		"transporter_name",
		"grand_total",
		"is_return",
		"status",
		"currency",
	],
	get_indicator: function (doc) {
		if (cint(doc.is_return) == 1 && doc.status == "Return") {
			return [__("Return"), "gray", "is_return,=,1"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "Return Issued") {
			return [__("Return Issued"), "grey", "status,=,Return Issued"];
		} else if (flt(doc.per_billed) == 0) {
			return [__("To Bill"), "orange", "per_billed,=,0|docstatus,=,1"];
		} else if (flt(doc.per_billed, 2) > 0 && flt(doc.per_billed, 2) < 100) {
			return [__("Partially Billed"), "yellow", "per_billed,<,100|docstatus,=,1"];
		} else if (flt(doc.per_billed, 2) === 100) {
			return [__("Completed"), "green", "per_billed,=,100|docstatus,=,1"];
		}
	},
	onload: function (doclist) {
		const action = () => {
			const selected_docs = doclist.get_checked_items();
			const docnames = doclist.get_checked_items(true);

			if (selected_docs.length > 0) {
				frappe.call({
					type: "POST",
					method: "frappe.model.mapper.map_docs",
					args: {
						method: "erpnext.stock.doctype.delivery_note.mapper.make_delivery_trip",
						source_names: docnames,
						target_doc: frappe.model.get_new_doc("Delivery Trip"),
					},
					callback: function (r) {
						if (!r.exc) {
							frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					},
				});
			}
		};

		if (frappe.model.can_create("Delivery Trip")) {
			doclist.page.add_action_item(__("Create Delivery Trip"), action);
		}

		if (frappe.model.can_create("Sales Invoice")) {
			doclist.page.add_action_item(__("Sales Invoice"), () => {
				erpnext.bulk_transaction_processing.create(doclist, "Delivery Note", "Sales Invoice");
			});
		}

		if (frappe.model.can_create("Packing Slip")) {
			doclist.page.add_action_item(__("Packaging Slip From Delivery Note"), () => {
				erpnext.bulk_transaction_processing.create(doclist, "Delivery Note", "Packing Slip");
			});
		}
	},
};
