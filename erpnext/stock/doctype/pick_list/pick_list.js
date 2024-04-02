// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pick List", {
	setup: (frm) => {
		frm.ignore_doctypes_on_cancel_all = ["Serial and Batch Bundle"];

		frm.set_indicator_formatter("item_code", function (doc) {
			return doc.stock_qty === 0 ? "red" : "green";
		});

		frm.custom_make_buttons = {
			"Delivery Note": "Delivery Note",
			"Stock Entry": "Stock Entry",
		};

		frm.set_query("parent_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("work_order", () => {
			return {
				query: "erpnext.stock.doctype.pick_list.pick_list.get_pending_work_orders",
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("material_request", () => {
			return {
				filters: {
					material_request_type: ["=", frm.doc.purpose],
				},
			};
		});

		frm.set_query("item_code", "locations", () => {
			return erpnext.queries.item({ is_stock_item: 1 });
		});

		frm.set_query("batch_no", "locations", (frm, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_batch_no",
				filters: {
					item_code: row.item_code,
					warehouse: row.warehouse,
				},
			};
		});

		frm.set_query("serial_and_batch_bundle", "locations", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					item_code: row.item_code,
					voucher_type: doc.doctype,
					voucher_no: ["in", [doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});
	},
	set_item_locations: (frm, save) => {
		if (!(frm.doc.locations && frm.doc.locations.length)) {
			frappe.msgprint(__("Add items in the Item Locations table"));
		} else {
			frappe.call({
				method: "set_item_locations",
				doc: frm.doc,
				args: {
					save: save,
				},
				freeze: 1,
				freeze_message: __("Setting Item Locations..."),
				callback(r) {
					refresh_field("locations");
				},
			});
		}
	},
	get_item_locations: (frm) => {
		// Button on the form
		frm.events.set_item_locations(frm, false);
	},
	refresh: (frm) => {
		frm.trigger("add_get_items_button");
		if (frm.doc.docstatus === 1) {
			frappe
				.xcall("erpnext.stock.doctype.pick_list.pick_list.target_document_exists", {
					pick_list_name: frm.doc.name,
					purpose: frm.doc.purpose,
				})
				.then((target_document_exists) => {
					frm.set_df_property("locations", "allow_on_submit", target_document_exists ? 0 : 1);

					if (target_document_exists) return;

					frm.add_custom_button(__("Update Current Stock"), () =>
						frm.trigger("update_pick_list_stock")
					);

					if (frm.doc.purpose === "Delivery") {
						frm.add_custom_button(
							__("Delivery Note"),
							() => frm.trigger("create_delivery_note"),
							__("Create")
						);
					} else {
						frm.add_custom_button(
							__("Stock Entry"),
							() => frm.trigger("create_stock_entry"),
							__("Create")
						);
					}
				});

			if (frm.doc.purpose === "Delivery" && frm.doc.status === "Open") {
				if (frm.doc.__onload && frm.doc.__onload.has_unreserved_stock) {
					frm.add_custom_button(
						__("Reserve"),
						() => frm.events.create_stock_reservation_entries(frm),
						__("Stock Reservation")
					);
				}

				if (frm.doc.__onload && frm.doc.__onload.has_reserved_stock) {
					frm.add_custom_button(
						__("Unreserve"),
						() => {
							frappe.confirm(
								__(
									"The reserved stock will be released. Are you certain you wish to proceed?"
								),
								() => frm.events.cancel_stock_reservation_entries(frm)
							);
						},
						__("Stock Reservation")
					);
					frm.add_custom_button(
						__("Reserved Stock"),
						() => frm.events.show_reserved_stock(frm),
						__("Stock Reservation")
					);
				}
			}
		}

		let sbb_field = frm.get_docfield("locations", "serial_and_batch_bundle");
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.item_code,
					warehouse: row.doc.warehouse,
					voucher_type: frm.doc.doctype,
				};
			};
		}
	},
	work_order: (frm) => {
		frappe.db
			.get_value("Work Order", frm.doc.work_order, ["qty", "material_transferred_for_manufacturing"])
			.then((data) => {
				let qty_data = data.message;
				let max = qty_data.qty - qty_data.material_transferred_for_manufacturing;
				frappe.prompt(
					{
						fieldtype: "Float",
						label: __("Qty of Finished Goods Item"),
						fieldname: "qty",
						description: __("Max: {0}", [max]),
						default: max,
					},
					(data) => {
						frm.set_value("for_qty", data.qty);
						if (data.qty > max) {
							frappe.msgprint(__("Quantity must not be more than {0}", [max]));
							return;
						}
						frm.clear_table("locations");
						erpnext.utils.map_current_doc({
							method: "erpnext.manufacturing.doctype.work_order.work_order.create_pick_list",
							target: frm,
							source_name: frm.doc.work_order,
						});
					},
					__("Select Quantity"),
					__("Get Items")
				);
			});
	},
	material_request: (frm) => {
		erpnext.utils.map_current_doc({
			method: "erpnext.stock.doctype.material_request.material_request.create_pick_list",
			target: frm,
			source_name: frm.doc.material_request,
		});
	},
	purpose: (frm) => {
		frm.clear_table("locations");
		frm.trigger("add_get_items_button");
	},
	create_delivery_note: (frm) => {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.pick_list.pick_list.create_delivery_note",
			frm: frm,
		});
	},
	create_stock_entry: (frm) => {
		frappe
			.xcall("erpnext.stock.doctype.pick_list.pick_list.create_stock_entry", {
				pick_list: frm.doc,
			})
			.then((stock_entry) => {
				frappe.model.sync(stock_entry);
				frappe.set_route("Form", "Stock Entry", stock_entry.name);
			});
	},
	update_pick_list_stock: (frm) => {
		frm.events.set_item_locations(frm, true);
	},
	add_get_items_button: (frm) => {
		let purpose = frm.doc.purpose;
		if (purpose != "Delivery" || frm.doc.docstatus !== 0) return;
		let get_query_filters = {
			docstatus: 1,
			per_delivered: ["<", 100],
			status: ["!=", ""],
			customer: frm.doc.customer,
		};
		frm.get_items_btn = frm.add_custom_button(__("Get Items"), () => {
			erpnext.utils.map_current_doc({
				method: "erpnext.selling.doctype.sales_order.sales_order.create_pick_list",
				source_doctype: "Sales Order",
				target: frm,
				setters: {
					company: frm.doc.company,
					customer: frm.doc.customer,
				},
				date_field: "transaction_date",
				get_query_filters: get_query_filters,
			});
		});
	},
	scan_barcode: (frm) => {
		const opts = {
			frm,
			items_table_name: "locations",
			qty_field: "picked_qty",
			max_qty_field: "qty",
			dont_allow_new_row: true,
			prompt_qty: frm.doc.prompt_qty,
			serial_no_field: "not_supported", // doesn't make sense for picklist without a separate field.
		};
		const barcode_scanner = new erpnext.utils.BarcodeScanner(opts);
		barcode_scanner.process_scan();
	},
	create_stock_reservation_entries: (frm) => {
		frappe.call({
			doc: frm.doc,
			method: "create_stock_reservation_entries",
			args: {
				notify: true,
			},
			freeze: true,
			freeze_message: __("Reserving Stock..."),
			callback: (r) => {
				frm.doc.__onload.has_unreserved_stock = false;
				frm.reload_doc();
			},
		});
	},
	cancel_stock_reservation_entries: (frm) => {
		frappe.call({
			doc: frm.doc,
			method: "cancel_stock_reservation_entries",
			args: {
				notify: true,
			},
			freeze: true,
			freeze_message: __("Unreserving Stock..."),
			callback: (r) => {
				frm.doc.__onload.has_reserved_stock = false;
				frm.reload_doc();
			},
		});
	},
	show_reserved_stock(frm) {
		// Get the latest modified date from the locations table.
		var to_date = moment(
			new Date(Math.max(...frm.doc.locations.map((e) => new Date(e.modified))))
		).format("YYYY-MM-DD");

		frappe.route_options = {
			company: frm.doc.company,
			from_date: moment(frm.doc.creation).format("YYYY-MM-DD"),
			to_date: to_date,
			voucher_type: "Sales Order",
			from_voucher_type: "Pick List",
			from_voucher_no: frm.doc.name,
		};
		frappe.set_route("query-report", "Reserved Stock");
	},
});

frappe.ui.form.on("Pick List Item", {
	item_code: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			get_item_details(row.item_code).then((data) => {
				frappe.model.set_value(cdt, cdn, "uom", data.stock_uom);
				frappe.model.set_value(cdt, cdn, "stock_uom", data.stock_uom);
				frappe.model.set_value(cdt, cdn, "conversion_factor", 1);
			});
		}
	},

	uom: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		if (row.uom) {
			get_item_details(row.item_code, row.uom).then((data) => {
				frappe.model.set_value(cdt, cdn, "conversion_factor", data.conversion_factor);
			});
		}
	},

	qty: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "stock_qty", row.qty * row.conversion_factor);
	},

	conversion_factor: (frm, cdt, cdn) => {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "stock_qty", row.qty * row.conversion_factor);
	},

	pick_serial_and_batch(frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		let path = "assets/erpnext/js/utils/serial_no_batch_selector.js";

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.qty > 0 ? "Outward" : "Inward";

				item.title = item.has_serial_no ? __("Select Serial No") : __("Select Batch No");

				if (item.has_serial_no && item.has_batch_no) {
					item.title = __("Select Serial and Batch");
				}

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						frappe.model.set_value(item.doctype, item.name, {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							qty: qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						});
					}
				});
			}
		});
	},
});

function get_item_details(item_code, uom = null) {
	if (item_code) {
		return frappe.xcall("erpnext.stock.doctype.pick_list.pick_list.get_item_details", {
			item_code,
			uom,
		});
	}
}
