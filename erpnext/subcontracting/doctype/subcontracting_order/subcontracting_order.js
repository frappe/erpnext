// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.buying");

erpnext.landed_cost_taxes_and_charges.setup_triggers("Subcontracting Order");

// client script for Subcontracting Order Item is not necessarily required as the server side code will do everything that is necessary.
// this is just so that the user does not get potentially confused
frappe.ui.form.on("Subcontracting Order Item", {
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

frappe.ui.form.on("Subcontracting Order", {
	setup: (frm) => {
		frm.get_field("items").grid.cannot_add_rows = true;
		frm.trigger("set_queries");

		frm.set_indicator_formatter("item_code", (doc) => (doc.qty <= doc.received_qty ? "green" : "orange"));

		frm.set_query("supplier_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("purchase_order", () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 1,
					is_old_subcontracting_flow: 0,
				},
			};
		});

		frm.set_query("cost_center", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("cost_center", "items", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query("set_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("warehouse", "items", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0,
			},
		}));

		frm.set_query("expense_account", "items", () => ({
			query: "erpnext.controllers.queries.get_expense_account",
			filters: {
				company: frm.doc.company,
			},
		}));

		frm.set_query("bom", "items", (doc, cdt, cdn) => {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1,
					docstatus: 1,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("set_reserve_warehouse", () => {
			return {
				filters: {
					company: frm.doc.company,
					name: ["!=", frm.doc.supplier_warehouse],
					is_group: 0,
				},
			};
		});
	},

	set_queries: (frm) => {
		frm.set_query("contact_person", erpnext.queries.contact_query);
		frm.set_query("supplier_address", erpnext.queries.address_query);

		frm.set_query("billing_address", erpnext.queries.company_address_query);

		frm.set_query("shipping_address", () => {
			return erpnext.queries.company_address_query(frm.doc);
		});
	},

	onload: (frm) => {
		if (!frm.doc.transaction_date) {
			frm.set_value("transaction_date", frappe.datetime.get_today());
		}
	},

	purchase_order: (frm) => {
		frm.set_value("service_items", null);
		frm.set_value("items", null);
		frm.set_value("supplied_items", null);

		if (frm.doc.purchase_order) {
			erpnext.utils.map_current_doc({
				method: "erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order",
				source_name: frm.doc.purchase_order,
				target_doc: frm,
				freeze: true,
				freeze_message: __("Mapping Subcontracting Order ..."),
			});
		}
	},

	refresh: function (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "supplier", doctype: "Supplier" };

		if (frm.doc.docstatus == 1 && frm.has_perm("submit")) {
			if (frm.doc.status == "Closed") {
				frm.add_custom_button(
					__("Re-open"),
					() => frm.events.update_subcontracting_order_status(frm),
					__("Status")
				);
			} else if (flt(frm.doc.per_received, 2) < 100) {
				frm.add_custom_button(
					__("Close"),
					() => frm.events.update_subcontracting_order_status(frm, "Closed"),
					__("Status")
				);
			}

			if (frm.doc.reserve_stock) {
				if (frm.doc.status !== "Closed") {
					if (frm.doc.__onload && frm.doc.__onload.has_unreserved_stock) {
						frm.add_custom_button(
							__("Reserve"),
							() => frm.events.create_stock_reservation_entries(frm),
							__("Stock Reservation")
						);
					}
				}

				if (
					frm.doc.__onload &&
					frm.doc.__onload.has_reserved_stock &&
					frappe.model.can_cancel("Stock Reservation Entry")
				) {
					frm.add_custom_button(
						__("Unreserve"),
						() => frm.events.cancel_stock_reservation_entries(frm),
						__("Stock Reservation")
					);
				}

				frm.doc.supplied_items.forEach((item) => {
					if (
						flt(item.stock_reserved_qty) > 0 &&
						frappe.model.can_read("Stock Reservation Entry")
					) {
						frm.add_custom_button(
							__("Reserved Stock"),
							() => frm.events.show_reserved_stock(frm),
							__("Stock Reservation")
						);
						return;
					}
				});
			}
		}

		frm.trigger("get_materials_from_supplier");
	},

	create_stock_reservation_entries(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Stock Reservation"),
			size: "extra-large",
			fields: [
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
							fieldname: "subcontracting_order_supplied_item",
							fieldtype: "Link",
							label: __("Subcontracting Order Supplied Item"),
							options: "Subcontracting Order Supplied Item",
							reqd: 1,
							in_list_view: 1,
							read_only: 1,
							get_query: () => {
								return {
									query: "erpnext.controllers.queries.get_filtered_child_rows",
									filters: {
										parenttype: frm.doc.doctype,
										parent: frm.doc.name,
									},
								};
							},
						},
						{
							fieldname: "rm_item_code",
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
							read_only: 1,
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
						method: "reserve_raw_materials",
						args: {
							items: data.items.map((item) => ({
								name: item.subcontracting_order_supplied_item,
								qty_to_reserve: item.qty_to_reserve,
							})),
						},
						freeze: true,
						freeze_message: __("Reserving Stock..."),
						callback: (_) => {
							frm.reload_doc();
						},
					});

					dialog.hide();
				} else {
					frappe.msgprint(__("Please select items to reserve."));
				}
			},
		});

		frm.doc.supplied_items.forEach((item) => {
			let unreserved_qty =
				flt(item.required_qty) - flt(item.supplied_qty) - flt(item.stock_reserved_qty);

			if (unreserved_qty > 0) {
				dialog.fields_dict.items.df.data.push({
					__checked: 1,
					subcontracting_order_supplied_item: item.name,
					rm_item_code: item.rm_item_code,
					warehouse: item.reserve_warehouse,
					qty_to_reserve: unreserved_qty,
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
						callback: (_) => {
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
					voucher_no: frm.doc.name,
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

	update_subcontracting_order_status(frm, status) {
		frappe.call({
			method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.update_subcontracting_order_status",
			args: {
				sco: frm.doc.name,
				status: status,
			},
			callback: function (r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			},
		});
	},

	company: function (frm) {
		erpnext.utils.set_letter_head(frm);
	},

	get_materials_from_supplier: function (frm) {
		let sco_rm_details = [];

		if (frm.doc.status != "Closed" && frm.doc.supplied_items) {
			frm.doc.supplied_items.forEach((d) => {
				if (d.total_supplied_qty > 0 && d.total_supplied_qty != d.consumed_qty) {
					sco_rm_details.push(d.name);
				}
			});
		}

		if (sco_rm_details && sco_rm_details.length) {
			frm.add_custom_button(
				__("Return of Components"),
				() => {
					frm.call({
						method: "erpnext.controllers.subcontracting_controller.get_materials_from_supplier",
						freeze: true,
						freeze_message: __("Creating Stock Entry"),
						args: {
							subcontract_order: frm.doc.name,
							rm_details: sco_rm_details,
							order_doctype: cur_frm.doc.doctype,
						},
						callback: function (r) {
							if (r && r.message) {
								const doc = frappe.model.sync(r.message);
								frappe.set_route("Form", doc[0].doctype, doc[0].name);
							}
						},
					});
				},
				__("Create")
			);
		}
	},
});

frappe.ui.form.on("Landed Cost Taxes and Charges", {
	amount: function (frm, cdt, cdn) {
		frm.events.set_base_amount(frm, cdt, cdn);
	},

	expense_account: function (frm, cdt, cdn) {
		frm.events.set_account_currency(frm, cdt, cdn);
	},
});

erpnext.buying.SubcontractingOrderController = class SubcontractingOrderController {
	setup() {
		this.frm.custom_make_buttons = {
			"Subcontracting Receipt": "Subcontracting Receipt",
			"Stock Entry": "Material to Supplier",
		};
	}

	refresh(doc) {
		var me = this;

		if (doc.docstatus == 1) {
			if (!["Closed", "Completed"].includes(doc.status)) {
				if (flt(doc.per_received) < 100) {
					this.frm.add_custom_button(
						__("Subcontracting Receipt"),
						this.make_subcontracting_receipt,
						__("Create")
					);
					if (me.has_unsupplied_items()) {
						this.frm.add_custom_button(
							__("Material to Supplier"),
							this.make_stock_entry,
							__("Transfer")
						);
					}
				}
				if (flt(doc.per_received) < 100 && me.has_unsupplied_items()) {
					this.frm.page.set_inner_btn_group_as_primary(__("Transfer"));
				} else {
					this.frm.page.set_inner_btn_group_as_primary(__("Create"));
				}
			}
		}
	}

	items_add(doc, cdt, cdn) {
		if (doc.set_warehouse) {
			var row = frappe.get_doc(cdt, cdn);
			row.warehouse = doc.set_warehouse;
		}
	}

	set_warehouse(doc) {
		this.set_warehouse_in_children(doc.items, "warehouse", doc.set_warehouse);
	}

	set_reserve_warehouse(doc) {
		this.set_warehouse_in_children(doc.supplied_items, "reserve_warehouse", doc.set_reserve_warehouse);
	}

	set_warehouse_in_children(child_table, warehouse_field, warehouse) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
	}

	has_unsupplied_items() {
		let over_transfer_allowance = this.frm.doc.__onload.over_transfer_allowance;
		return this.frm.doc["supplied_items"].some((item) => {
			let required_qty = item.required_qty + (item.required_qty * over_transfer_allowance) / 100;
			return required_qty > item.supplied_qty - item.returned_qty;
		});
	}

	make_subcontracting_receipt() {
		frappe.model.open_mapped_doc({
			method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
			frm: cur_frm,
			freeze_message: __("Creating Subcontracting Receipt ..."),
		});
	}

	make_stock_entry() {
		frappe.call({
			method: "erpnext.controllers.subcontracting_controller.make_rm_stock_entry",
			args: {
				subcontract_order: cur_frm.doc.name,
				order_doctype: cur_frm.doc.doctype,
			},
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.buying.SubcontractingOrderController({ frm: cur_frm }));
