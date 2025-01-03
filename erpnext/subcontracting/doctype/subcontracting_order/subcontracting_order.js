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
			row.qty * row.sc_conversion_factor
		);
		frappe.model.set_value(service_item.doctype, service_item.name, "fg_item_qty", row.qty);
		frappe.model.set_value(
			service_item.doctype,
			service_item.name,
			"amount",
			row.qty * row.sc_conversion_factor * service_item.rate
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
		}

		frm.trigger("get_materials_from_supplier");
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
					cur_frm.add_custom_button(
						__("Subcontracting Receipt"),
						this.make_subcontracting_receipt,
						__("Create")
					);
					if (me.has_unsupplied_items()) {
						cur_frm.add_custom_button(
							__("Material to Supplier"),
							this.make_stock_entry,
							__("Transfer")
						);
					}
				}
				cur_frm.page.set_inner_btn_group_as_primary(__("Create"));
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
