// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Goods Inward Note", {
	setup(frm) {
		frm.set_query("order", (doc) => {
			const filters = { docstatus: 1, status: ["!=", "Closed"] };
			if (doc.supplier) {
				filters.supplier = doc.supplier;
			}
			return { filters };
		});
		frm.set_query("transporter", () => ({ filters: { is_transporter: 1 } }));
		frm.set_query("current_inward_location", () => ({ filters: { disabled: 0 } }));
		frm.set_query("item_code", "items", (doc) => {
			if (doc.order_type && doc.order) {
				const child_doctype =
					doc.order_type === "Purchase Order" ? "Purchase Order Item" : "Subcontracting Order Item";
				return {
					query: "erpnext.controllers.queries.get_filtered_child_rows",
					filters: { parenttype: child_doctype, parent: doc.order },
				};
			}
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new() && frappe.model.can_create("Quality Inspection")) {
			frm.add_custom_button(
				__("Quality Inspection(s)"),
				() => {
					let transaction_controller = new erpnext.TransactionController({ frm: frm });
					transaction_controller.make_quality_inspection();
				},
				__("Create")
			);
		}

		const quality_inspection_field = frm.get_docfield("items", "quality_inspection");
		quality_inspection_field.get_route_options_for_new_doc = function (row) {
			if (frm.is_new()) return {};
			return {
				inspection_type: "Incoming",
				reference_type: frm.doc.doctype,
				reference_name: frm.doc.name,
				item_code: row.doc.item_code,
			};
		};

		if (frm.doc.docstatus === 1 && ["In Custody", "Partially Received"].includes(frm.doc.status)) {
			const receipt_label =
				frm.doc.order_type === "Purchase Order"
					? __("Purchase Receipt")
					: __("Subcontracting Receipt");
			frm.add_custom_button(
				receipt_label,
				() => {
					frappe.call({
						method: "erpnext.stock.services.goods_inward.make_receipt_from_goods_inward_note",
						args: { goods_inward_note: frm.doc.name },
						freeze: true,
						callback: (r) => {
							const doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						},
					});
				},
				__("Create")
			);
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},

	order(frm) {
		if (frm.doc.order && frm.doc.docstatus === 0) {
			frm.call("get_items_from_order").then(() => {
				frm.refresh_field("items");
			});
		}
	},

	gross_weight(frm) {
		frm.set_value("net_weight", flt(frm.doc.gross_weight) - flt(frm.doc.tare_weight));
	},

	tare_weight(frm) {
		frm.set_value("net_weight", flt(frm.doc.gross_weight) - flt(frm.doc.tare_weight));
	},
});
