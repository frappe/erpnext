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
		"company",
	],
	get_indicator: function (doc) {
		if (cint(doc.is_return) == 1 && doc.status == "Return") {
			return [__("Return"), "gray", "is_return,=,1"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.status === "Return Issued") {
			return [__("Return Issued"), "grey", "status,=,Return Issued"];
		} else if (flt(doc.per_billed) == 0) {
			return [__("To Bill"), "orange", "status,=,To Bill"];
		} else if (flt(doc.per_billed, 2) > 0 && flt(doc.per_billed, 2) < 100) {
			return [__("Partially Billed"), "yellow", "status,=,Partially Billed"];
		} else if (flt(doc.per_billed, 2) === 100) {
			return [__("Completed"), "green", "status,=,Completed"];
		}
	},
	onload: function (doclist) {
		const action = () => {
			const selected_docs = doclist.get_checked_items();
			const docnames = doclist.get_checked_items(true);

			if (selected_docs.length > 0) {
<<<<<<< HEAD
				frappe.new_doc("Delivery Trip").then(() => {
					// Empty out the child table before inserting new ones
					cur_frm.set_value("delivery_stops", []);

					// We don't want to use `map_current_doc` since it brings up
					// the dialog to select more items. We just want the mapper
					// function to be called.
					frappe.call({
						type: "POST",
						method: "frappe.model.mapper.map_docs",
						args: {
							method: "erpnext.stock.doctype.delivery_note.delivery_note.make_delivery_trip",
							source_names: docnames,
							target_doc: cur_frm.doc,
						},
						callback: function (r) {
							if (!r.exc) {
								frappe.model.sync(r.message);
								cur_frm.dirty();
								cur_frm.refresh();
							}
						},
					});
=======
				const target_doc = frappe.model.get_new_doc("Delivery Trip");
				target_doc.company = selected_docs[0].company;

				frappe.call({
					type: "POST",
					method: "frappe.model.mapper.map_docs",
					args: {
						method: "erpnext.stock.doctype.delivery_note.mapper.make_delivery_trip",
						source_names: docnames,
						target_doc: target_doc,
					},
					callback: function (r) {
						if (!r.exc) {
							frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					},
>>>>>>> bbd2c65 (fix(stock): create the Delivery Trip from the Delivery Note list in its company)
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
