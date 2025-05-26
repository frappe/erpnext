// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// client script for Subcontracting Inward Order Item is not necessarily required as the server side code will do everything that is necessary.
// this is just so that the user does not get potentially confused
frappe.ui.form.on("Subcontracting Inward Order Item", {
	qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", row.qty * row.rate);
		const service_item = frm.doc.service_items[row.idx - 1];
		frappe.model.set_value(
			service_item.doctype,
			service_item.name,
			"qty",
			row.qty * row.subcontracting_conversion_factor
		);
		frappe.model.set_value(service_item.doctype, service_item.name, "fg_item_qty", row.qty);
		frappe.model.set_value(
			service_item.doctype,
			service_item.name,
			"amount",
			row.qty * row.subcontracting_conversion_factor * service_item.rate
		);
	},
	before_items_remove(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frm.toggle_enable(["service_items"], true);
		frm.get_field("service_items").grid.grid_rows[row.idx - 1].remove();
		frm.toggle_enable(["service_items"], false);
	},
});

frappe.ui.form.on("Subcontracting Inward Order", {
	setup: (frm) => {
		frm.get_field("items").grid.cannot_add_rows = true;
		frm.trigger("set_queries");

		frm.set_indicator_formatter("item_code", (doc) => (doc.qty <= doc.received_qty ? "green" : "orange"));

		frm.set_query("raw_materials_receipt_warehouse", () => {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("sales_order", () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 1,
				},
			};
		});
	},

	onload: (frm) => {
		if (!frm.doc.transaction_date) {
			frm.set_value("transaction_date", frappe.datetime.get_today());
		}
	},

	sales_order: (frm) => {
		frm.set_value("service_items", null);
		frm.set_value("items", null);
		frm.set_value("received_items", null);

		if (frm.doc.sales_order) {
			erpnext.utils.map_current_doc({
				method: "erpnext.selling.doctype.sales_order.sales_order.make_subcontracting_inward_order",
				source_name: frm.doc.sales_order,
				target_doc: frm,
				freeze: true,
				freeze_message: __("Mapping Subcontracting Inward Order ..."),
			});
		}
	},

	refresh: function (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "customer", doctype: "Customer" };

		if (frm.doc.docstatus == 1 && frm.has_perm("submit")) {
			if (frm.doc.status == "Closed") {
				frm.add_custom_button(
					__("Re-open"),
					() => frm.events.update_subcontracting_inward_order_status(frm),
					__("Status")
				);
			} else if (flt(frm.doc.per_delivered, 2) < 100) {
				frm.add_custom_button(
					__("Close"),
					() => frm.events.update_subcontracting_inward_order_status(frm, "Closed"),
					__("Status")
				);
			}
		}
	},

	update_subcontracting_inward_order_status(frm, status) {
		frappe.call({
			method: "erpnext.subcontracting.doctype.subcontracting_inward_order.subcontracting_inward_order.update_subcontracting_inward_order_status",
			args: {
				scio: frm.doc.name,
				status: status,
			},
			callback: function (r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
		});
	},

	create_stock_reservation_entries(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Stock Reservation"),
			size: "extra-large",
			fields: [
				{
					fieldname: "add_item",
					fieldtype: "Link",
					label: __("Add Item"),
					options: "Subcontracting Inward Order Received Item",
					get_query: () => {
						return {
							query: "erpnext.controllers.queries.get_filtered_child_rows",
							filters: {
								parenttype: frm.doc.doctype,
								parent: frm.doc.name,
							},
						};
					},
					onchange: () => {
						let sci_order_received_item = dialog.get_value("add_item");

						if (sci_order_received_item) {
							frm.doc.received_items.forEach((item) => {
								if (item.name === sci_order_received_item) {
									let unreserved_qty = item.received_qty - item.reserved_qty;

									if (unreserved_qty > 0) {
										dialog.fields_dict.items.df.data.forEach((row) => {
											if (row.sci_order_received_item === sci_order_received_item) {
												unreserved_qty -= row.qty_to_reserve;
											}
										});
									}

									dialog.fields_dict.items.df.data.push({
										sci_order_received_item: item.name,
										item_code: item.rm_item_code,
										qty_to_reserve: Math.max(unreserved_qty, 0),
									});
									dialog.fields_dict.items.grid.refresh();
									dialog.set_value("add_item", undefined);
								}
							});
						}
					},
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "reserve_warehouse",
					fieldtype: "Link",
					label: __("Reserve Warehouse"),
					options: "Warehouse",
					read_only: 1,
					default: frm.doc.raw_materials_receipt_warehouse,
				},
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
							fieldname: "sci_order_received_item",
							fieldtype: "Link",
							label: __("Subcontracting Inward Order Received Item"),
							options: "Subcontracting Inward Order Received Item",
							reqd: 1,
							in_list_view: 1,
							get_query: () => {
								return {
									query: "erpnext.controllers.queries.get_filtered_child_rows",
									filters: {
										parenttype: frm.doc.doctype,
										parent: frm.doc.name,
									},
								};
							},
							onchange: (event) => {
								if (event) {
									let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
									let item_row =
										dialog.fields_dict.items.grid.grid_rows_by_docname[name].doc;

									frm.doc.received_items.forEach((item) => {
										if (item.name === item_row.sci_order_received_item) {
											item_row.item_code = item.rm_item_code;
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
							fieldname: "qty_to_reserve",
							fieldtype: "Float",
							label: __("Qty"),
							reqd: 1,
							in_list_view: 1,
						},
					],
				},
			],
			primary_action_label: __("Reserve Stock"),
			primary_action: () => {
				var data = { items: dialog.fields_dict.items.grid.get_selected_children() };

				if (data.items && data.items.length > 0) {
					frappe.call({
						doc: frm.doc,
						method: "create_stock_reservation_entries",
						args: {
							items_details: data.items,
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
		});

		frm.doc.received_items.forEach((item) => {
			if (item.received_qty - item.reserved_qty > 0) {
				dialog.fields_dict.items.df.data.push({
					__checked: 1,
					sci_order_received_item: item.name,
					item_code: item.rm_item_code,
					qty_to_reserve: item.received_qty - item.reserved_qty,
				});
			}
		});

		dialog.fields_dict.items.grid.refresh();
		dialog.show();
	},

	cancel_stock_reservation_entries(frm) {
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
					fields: [
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
					],
				},
			],
			primary_action_label: __("Unreserve Stock"),
			primary_action: () => {
				var data = { sr_entries: dialog.fields_dict.sr_entries.grid.get_selected_children() };

				if (data.sr_entries && data.sr_entries.length > 0) {
					frappe.call({
						doc: frm.doc,
						method: "cancel_stock_reservation_entries",
						args: {
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
		});

		frappe
			.call({
				method: "erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry.get_stock_reservation_entries_for_voucher",
				args: {
					voucher_type: frm.doctype,
					voucher_no: frm.docname,
				},
				callback: (r) => {
					if (!r.exc && r.message) {
						r.message.forEach((sre) => {
							if (flt(sre.reserved_qty) > flt(sre.delivered_qty)) {
								dialog.fields_dict.sr_entries.df.data.push({
									sre: sre.name,
									item_code: sre.item_code,
									warehouse: sre.warehouse,
									qty: flt(sre.reserved_qty) - flt(sre.delivered_qty),
								});
							}
						});
					}
				},
			})
			.then((r) => {
				dialog.fields_dict.sr_entries.grid.refresh();
				dialog.show();
			});
	},

	show_reserved_stock(frm) {
		// Get the latest modified date from the items table.
		var to_date = moment(new Date(Math.max(...frm.doc.items.map((e) => new Date(e.modified))))).format(
			"YYYY-MM-DD"
		);

		frappe.route_options = {
			company: frm.doc.company,
			from_date: frm.doc.transaction_date,
			to_date: to_date,
			voucher_type: frm.doc.doctype,
			voucher_no: frm.doc.name,
		};
		frappe.set_route("query-report", "Reserved Stock");
	},

	make_work_order(frm) {
		frappe.call({
			method: "make_work_order",
			freeze: true,
			doc: frm.doc,
			callback: function () {
				frm.reload_doc();
			},
		});
	},
});

erpnext.selling.SubcontractingInwardOrderController = class SubcontractingInwardOrderController {
	setup() {
		this.frm.custom_make_buttons = {
			"Subcontracting Delivery": "Subcontracting Delivery",
			"Stock Entry": "Material from Customer",
		};
	}

	refresh(doc) {
		var me = this;

		if (doc.__onload && doc.__onload.has_unreserved_stock) {
			me.frm.add_custom_button(
				__("Reserve"),
				() => me.frm.events.create_stock_reservation_entries(me.frm),
				__("Stock Reservation")
			);
		}

		if (
			doc.__onload &&
			doc.__onload.has_reserved_stock &&
			frappe.model.can_cancel("Stock Reservation Entry")
		) {
			me.frm.add_custom_button(
				__("Unreserve"),
				() => me.frm.events.cancel_stock_reservation_entries(me.frm),
				__("Stock Reservation")
			);
		}

		doc.received_items.forEach((item) => {
			if (flt(item.reserved_qty) > 0 && frappe.model.can_read("Stock Reservation Entry")) {
				me.frm.add_custom_button(
					__("Reserved Stock"),
					() => me.frm.events.show_reserved_stock(me.frm),
					__("Stock Reservation")
				);
				return;
			}
		});

		if (doc.docstatus == 1) {
			if (!["Closed", "Completed"].includes(doc.status)) {
				if (
					doc.received_items.some(
						(item) => item.received_qty - item.work_order_qty - item.returned_qty > 0
					)
				) {
					this.frm.add_custom_button(
						__("Raw Materials to Customer"),
						() => this.frm.trigger("make_rm_return"),
						__("Return")
					);
				}
				if (doc.per_produced < 100) {
					this.frm.add_custom_button(
						__("Work Order"),
						() => this.frm.trigger("make_work_order"),
						__("Create")
					);
					this.frm.add_custom_button(
						__("Material from Customer"),
						this.make_stock_entry,
						__("Receive")
					);
				}
				if (doc.per_delivered < 100) {
					this.frm.add_custom_button(
						__("Subcontracting Delivery"),
						this.make_subcontracting_delivery,
						__("Create")
					);
				}
				if (doc.per_produced < 100) {
					this.frm.page.set_inner_btn_group_as_primary(__("Receive"));
				} else {
					this.frm.page.set_inner_btn_group_as_primary(__("Create"));
				}
			}
		}
	}

	make_subcontracting_delivery() {
		frappe.model.open_mapped_doc({
			method: "erpnext.subcontracting.doctype.subcontracting_inward_order.subcontracting_inward_order.make_subcontracting_delivery",
			frm: cur_frm,
			freeze_message: __("Creating Subcontracting Delivery ..."),
		});
	}

	make_stock_entry() {
		frappe.call({
			method: "erpnext.controllers.subcontracting_controller.make_rm_stock_entry_inward",
			args: {
				subcontract_inward_order: cur_frm.doc.name,
			},
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	}

	make_rm_return() {
		frappe.call({
			method: "erpnext.controllers.subcontracting_controller.make_rm_return",
			args: {
				subcontract_inward_order: cur_frm.doc.name,
			},
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.selling.SubcontractingInwardOrderController({ frm: cur_frm }));
