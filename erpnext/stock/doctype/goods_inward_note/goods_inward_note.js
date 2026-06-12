// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Goods Inward Note", {
	onload_post_render(frm) {
		// arriving from an order's Create button sets the order through route
		// options, which apply after onload and fire no field trigger — fetch
		// the rows the same way picking the order by hand would
		const has_rows = (frm.doc.items || []).some((row) => row.item_code);
		if (frm.is_new() && frm.doc.order && !has_rows) {
			frm.trigger("order");
		}
	},

	setup(frm) {
		frm.set_query("order", (doc) => {
			const filters = { docstatus: 1, status: ["!=", "Closed"] };
			if (doc.supplier) {
				filters.supplier = doc.supplier;
			}
			if (doc.order_type === "Purchase Order") {
				// a subcontracted order's goods arrive against its Subcontracting Order
				filters.is_subcontracted = 0;
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
		// quality is inspected in custody, after the arrival is recorded —
		// the note submits regardless, the receipt waits for the verdict
		if (
			frm.doc.docstatus === 1 &&
			["In Custody", "Partially Received"].includes(frm.doc.status) &&
			frappe.model.can_create("Quality Inspection")
		) {
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
				child_row_reference: row.doc.name,
				item_code: row.doc.item_code,
			};
		};

		if (frm.doc.docstatus === 1 && ["In Custody", "Partially Received"].includes(frm.doc.status)) {
			const receive_via = (label, method) => {
				frm.add_custom_button(
					label,
					() => {
						frappe.call({
							method: "erpnext.stock.services.goods_inward." + method,
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
			};
			if (frm.doc.order_type === "Purchase Order") {
				receive_via(__("Purchase Receipt"), "make_receipt_from_goods_inward_note");
				// receive and bill in one document
				receive_via(__("Purchase Invoice"), "make_invoice_from_goods_inward_note");
			} else {
				receive_via(__("Subcontracting Receipt"), "make_receipt_from_goods_inward_note");
			}
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

frappe.ui.form.on("Goods Inward Note Item", {
	qty(frm, cdt, cdn) {
		// keep the stock-unit hint honest while the operator corrects the count
		const row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "stock_qty", flt(row.qty) * (flt(row.conversion_factor) || 1));
	},
});
