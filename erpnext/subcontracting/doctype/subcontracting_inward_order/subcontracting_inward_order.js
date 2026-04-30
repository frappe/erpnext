// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// client script for Subcontracting Inward Order Item is not necessarily required as the server side code will do everything that is necessary.
// this is just so that the user does not get potentially confused
frappe.ui.form.on("Subcontracting Inward Order Item", {
	qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const service_item = frm.doc.service_items[row.idx - 1];
		frappe.model.set_value(
			service_item.doctype,
			service_item.name,
			"qty",
			row.qty * row.subcontracting_conversion_factor
		);
		frappe.model.set_value(service_item.doctype, service_item.name, "fg_item_qty", row.qty);
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

		frm.set_query("customer_warehouse", () => {
			return {
				filters: {
					is_group: 0,
					is_rejected_warehouse: 0,
					company: frm.doc.company,
					customer: frm.doc.customer,
					disabled: 0,
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

		frm.set_query("delivery_warehouse", "items", () => {
			return {
				filters: {
					is_group: 0,
					is_rejected_warehouse: 0,
					company: frm.doc.company,
					disabled: 0,
					customer: ["is", "not set"],
				},
			};
		});

		frm.set_query("bom", "items", () => {
			return {
				filters: {
					is_active: 1,
				},
			};
		});

		frm.set_query("set_delivery_warehouse", () => {
			return {
				filters: {
					is_group: 0,
					is_rejected_warehouse: 0,
					company: frm.doc.company,
					disabled: 0,
					customer: ["is", "not set"],
				},
			};
		});
	},

	set_delivery_warehouse: (frm) => {
		frm.doc.items.forEach((item) =>
			frappe.model.set_value(
				item.doctype,
				item.name,
				"delivery_warehouse",
				frm.doc.set_delivery_warehouse
			)
		);
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
		if (frm.doc.docstatus == 1) {
			if (frm.has_perm("submit")) {
				if (frm.doc.status == "Closed") {
					frm.add_custom_button(
						__("Re-open"),
						() => frm.events.update_subcontracting_inward_order_status(frm),
						__("Status")
					);
				} else {
					frm.add_custom_button(
						__("Close"),
						() => frm.events.update_subcontracting_inward_order_status(frm, "Closed"),
						__("Status")
					);
				}
			}
			if (frm.doc.status != "Closed") {
				const is_raw_materials_received = frm.doc.received_items.some((item) =>
					item.is_customer_provided_item
						? item.received_qty - item.work_order_qty - item.returned_qty > 0
						: false
				);
				if (is_raw_materials_received) {
					frm.add_custom_button(
						__("Raw Materials to Customer"),
						() => frm.trigger("make_rm_return"),
						__("Return")
					);
					if (frm.doc.per_produced < 100) {
						frm.add_custom_button(
							__("Work Order"),
							() => frm.events.make_work_order(frm),
							__("Create")
						);
					}
				}

				if (frm.doc.per_produced < 100) {
					frm.add_custom_button(
						__("Material from Customer"),
						() => frm.events.make_stock_entry(frm),
						__("Receive")
					);
				}
				if (frm.doc.per_produced > 0 && frm.doc.per_delivered < 100) {
					frm.add_custom_button(
						__("Subcontracting Delivery"),
						() => frm.events.make_subcontracting_delivery(frm),
						__("Create")
					);
				}
				if (frm.doc.per_delivered > 0 && frm.doc.per_returned < 100) {
					frm.add_custom_button(
						__("Finished Goods Return"),
						() => frm.events.make_subcontracting_return(frm),
						__("Return")
					);
				}
				if (frm.doc.per_produced < 100) {
					frm.page.set_inner_btn_group_as_primary(__("Receive"));
				} else if (frm.doc.per_delivered < 100) {
					frm.page.set_inner_btn_group_as_primary(__("Create"));
				} else if (frm.doc.per_delivered >= 100 && frm.doc.per_returned < 100) {
					frm.page.set_inner_btn_group_as_primary(__("Return"));
				}
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

	make_stock_entry(frm) {
		frappe.call({
			method: "make_rm_stock_entry_inward",
			freeze: true,
			doc: frm.doc,
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	make_rm_return(frm) {
		frappe.call({
			method: "make_rm_return",
			freeze: true,
			doc: frm.doc,
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	make_subcontracting_delivery(frm) {
		frappe.call({
			method: "make_subcontracting_delivery",
			freeze: true,
			doc: frm.doc,
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},

	make_subcontracting_return(frm) {
		frappe.call({
			method: "make_subcontracting_return",
			freeze: true,
			doc: frm.doc,
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			},
		});
	},
});
