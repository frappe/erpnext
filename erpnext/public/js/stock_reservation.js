frappe.provide("erpnext.stock_reservation");

$.extend(erpnext.stock_reservation, {
	make_entries(frm, table_name) {
		erpnext.stock_reservation.setup(frm, table_name);
	},

	setup(frm, table_name) {
		let parms = erpnext.stock_reservation.get_parms(frm, table_name);

		erpnext.stock_reservation.dialog = new frappe.ui.Dialog({
			title: __("Stock Reservation"),
			size: "extra-large",
			fields: erpnext.stock_reservation.get_dialog_fields(frm, parms),
			primary_action_label: __("Reserve Stock"),
			primary_action: () => {
				erpnext.stock_reservation.reserve_stock(frm, parms);
			},
		});

		erpnext.stock_reservation.render_items(frm, parms);
	},

	get_parms(frm, table_name) {
		let params = {
			table_name: table_name || "items",
			child_doctype: frm.doc.doctype + " Item",
		};

		params["qty_field"] = {
			"Sales Order": "stock_qty",
			"Work Order": "required_qty",
		}[frm.doc.doctype];

		params["dispatch_qty_field"] = {
			"Sales Order": "delivered_qty",
			"Work Order": "transferred_qty",
		}[frm.doc.doctype];

		params["method"] = {
			"Sales Order": "delivered_qty",
			"Work Order":
				"erpnext.manufacturing.doctype.work_order.work_order.make_stock_reservation_entries",
		}[frm.doc.doctype];

		return params;
	},

	get_dialog_fields(frm, parms) {
		let fields = erpnext.stock_reservation.fields || [];
		let qty_field = parms.qty_field;
		let dialog = erpnext.stock_reservation.dialog;

		let table_fields = [
			{ fieldtype: "Section Break" },
			{
				fieldname: "items",
				fieldtype: "Table",
				label: __("Items to Reserve"),
				allow_bulk_edit: false,
				cannot_add_rows: true,
				cannot_delete_rows: true,
				data: [],
				fields: [
					{
						fieldname: frappe.scrub(parms.child_doctype),
						fieldtype: "Link",
						label: __(parms.child_doctype),
						options: parms.child_doctype,
						reqd: 1,
						in_list_view: 1,
						get_query: () => {
							return {
								query: "erpnext.controllers.queries.get_filtered_child_rows",
								filters: {
									parenttype: frm.doc.doctype,
									parent: frm.doc.name,
									reserve_stock: 1,
								},
							};
						},
						onchange: (event) => {
							if (event) {
								let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
								let item_row = dialog.fields_dict.items.grid.grid_rows_by_docname[name].doc;

								frm.doc.items.forEach((item) => {
									if (item.name === item_row.sales_order_item) {
										item_row.item_code = item.item_code;
									}
								});
								dialog.fields_dict.items.grid.refresh();
							}
						},
					},
					{
						fieldname: "item_code",
						fieldtype: "Link",
						label: __("Item Code"),
						options: "Item",
						reqd: 1,
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "warehouse",
						fieldtype: "Link",
						label: __("Warehouse"),
						options: "Warehouse",
						reqd: 1,
						in_list_view: 1,
						get_query: () => {
							return {
								filters: [["Warehouse", "is_group", "!=", 1]],
							};
						},
					},
					{
						fieldname: qty_field,
						fieldtype: "Float",
						label: __("Qty"),
						reqd: 1,
						in_list_view: 1,
					},
				],
			},
		];

		return fields.concat(table_fields);
	},

	render_items(frm, parms) {
		let dialog = erpnext.stock_reservation.dialog;
		let field = frappe.scrub(parms.child_doctype);

		let qty_field = parms.qty_field;
		let dispatch_qty_field = parms.dispatch_qty_field;

		if (frm.doc.doctype === "Work Order" && frm.doc.skip_transfer) {
			dispatch_qty_field = "consumed_qty";
		}

		frm.doc[parms.table_name].forEach((item) => {
			if (frm.doc.reserve_stock) {
				let unreserved_qty =
					(flt(item[qty_field]) -
						(item.stock_reserved_qty
							? flt(item.stock_reserved_qty)
							: flt(item[dispatch_qty_field]) * flt(item.conversion_factor || 1))) /
					flt(item.conversion_factor || 1);

				if (unreserved_qty > 0) {
					let args = {
						__checked: 1,
						item_code: item.item_code,
						warehouse: item.warehouse || item.source_warehouse,
					};

					args[field] = item.name;
					args[qty_field] = unreserved_qty;
					dialog.fields_dict.items.df.data.push(args);
				}
			}
		});

		dialog.fields_dict.items.grid.refresh();
		dialog.show();
	},

	reserve_stock(frm, parms) {
		let dialog = erpnext.stock_reservation.dialog;
		var data = { items: dialog.fields_dict.items.grid.get_selected_children() };

		if (data.items && data.items.length > 0) {
			frappe.call({
				method: parms.method,
				args: {
					doc: frm.doc,
					items: data.items,
					notify: true,
				},
				freeze: true,
				freeze_message: __("Reserving Stock..."),
				callback: (r) => {
					frm.doc.__onload.has_unreserved_stock = false;
					frm.reload_doc();
				},
			});

			dialog.hide();
		} else {
			frappe.msgprint(__("Please select items to reserve."));
		}
	},

	unreserve_stock(frm) {
		erpnext.stock_reservation.get_stock_reservation_entries(frm.doctype, frm.docname).then((r) => {
			if (!r.exc && r.message) {
				if (r.message.length > 0) {
					erpnext.stock_reservation.prepare_for_cancel_sre_entries(frm, r.message);
				} else {
					frappe.msgprint(__("No reserved stock to unreserve."));
				}
			}
		});
	},

	prepare_for_cancel_sre_entries(frm, sre_entries) {
		const dialog = new frappe.ui.Dialog({
			title: __("Stock Unreservation"),
			size: "extra-large",
			fields: [
				{
					fieldname: "sr_entries",
					fieldtype: "Table",
					label: __("Reserved Stock"),
					allow_bulk_edit: false,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					data: [],
					fields: erpnext.stock_reservation.get_fields_for_cancel(),
				},
			],
			primary_action_label: __("Unreserve Stock"),
			primary_action: () => {
				erpnext.stock_reservation.cancel_stock_reservation(dialog, frm);
			},
		});

		sre_entries.forEach((sre) => {
			dialog.fields_dict.sr_entries.df.data.push({
				sre: sre.name,
				item_code: sre.item_code,
				warehouse: sre.warehouse,
				qty: flt(sre.reserved_qty) - flt(sre.delivered_qty),
			});
		});

		dialog.fields_dict.sr_entries.grid.refresh();
		dialog.show();
	},

	cancel_stock_reservation(dialog, frm) {
		var data = { sr_entries: dialog.fields_dict.sr_entries.grid.get_selected_children() };

		if (data.sr_entries?.length > 0) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.work_order.work_order.cancel_stock_reservation_entries",
				args: {
					doc: frm.doc,
					sre_list: data.sr_entries.map((item) => item.sre),
				},
				freeze: true,
				freeze_message: __("Unreserving Stock..."),
				callback: (r) => {
					frm.doc.__onload.has_reserved_stock = false;
					frm.reload_doc();
				},
			});

			dialog.hide();
		} else {
			frappe.msgprint(__("Please select items to unreserve."));
		}
	},

	get_stock_reservation_entries(voucher_type, voucher_no) {
		return frappe.call({
			method: "erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry.get_stock_reservation_entries_for_voucher",
			args: {
				voucher_type: voucher_type,
				voucher_no: voucher_no,
			},
		});
	},

	get_fields_for_cancel() {
		return [
			{
				fieldname: "sre",
				fieldtype: "Link",
				label: __("Stock Reservation Entry"),
				options: "Stock Reservation Entry",
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldname: "item_code",
				fieldtype: "Link",
				label: __("Item Code"),
				options: "Item",
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldname: "warehouse",
				fieldtype: "Link",
				label: __("Warehouse"),
				options: "Warehouse",
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
			{
				fieldname: "qty",
				fieldtype: "Float",
				label: __("Qty"),
				reqd: 1,
				read_only: 1,
				in_list_view: 1,
			},
		];
	},

	show_reserved_stock(frm, table_name) {
		if (!table_name) {
			table_name = "items";
		}

		// Get the latest modified date from the items table.
		var to_date = moment(
			new Date(Math.max(...frm.doc[table_name].map((e) => new Date(e.modified))))
		).format("YYYY-MM-DD");

		let from_date = frm.doc.transaction_date || new Date(frm.doc.creation);

		frappe.route_options = {
			company: frm.doc.company,
			from_date: from_date,
			to_date: to_date,
			voucher_type: frm.doc.doctype,
			voucher_no: frm.doc.name,
		};
		frappe.set_route("query-report", "Reserved Stock");
	},
});
