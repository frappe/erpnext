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
