frappe.listview_settings['Delivery Note'] = {
	add_fields: ["grand_total", "is_return", "per_billed", "status", "currency"],
	get_indicator: function (doc) {
		if (cint(doc.is_return) == 1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		} else if (doc.status === "Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		} else if (doc.grand_total !== 0 && flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (doc.grand_total === 0 || flt(doc.per_billed, 2) == 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	},
	onload: function (doclist) {
		const action = () => {
			const selected_docs = doclist.get_checked_items();
			const docnames = doclist.get_checked_items(true);

			if (selected_docs.length > 0) {
				for (let doc of selected_docs) {
					if (doc.docstatus !== 1 || doc.is_return) {
						frappe.throw(__("Cannot create a Delivery Trip from 'Cancelled', 'Draft' or 'Return' Delivery Notes."));
					}
				};

				frappe.new_doc("Delivery Trip")
					.then(() => {
						// Empty out the child table before inserting new ones
						cur_frm.set_value("delivery_stops", []);

						// We don't want to use `map_current_doc` since it brings up
						// the dialog to select more items. We just want the mapper
						// function to be called.
						frappe.call({
							type: "POST",
							method: "frappe.model.mapper.map_docs",
							args: {
								"method": "erpnext.stock.doctype.delivery_note.delivery_note.make_delivery_trip",
								"source_names": docnames,
								"target_doc": cur_frm.doc
							},
							callback: function (r) {
								if (!r.exc) {
									frappe.model.sync(r.message);
									cur_frm.dirty();
									cur_frm.refresh();
								}
							}
						});
					})
			};
		};

		doclist.page.add_actions_menu_item(__('Create Delivery Trip'), action, false);
	}
};
