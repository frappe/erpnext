frappe.ui.form.on("Sales Forecast", {
	refresh(frm) {
		frm.trigger("set_query_filters");
		frm.trigger("set_custom_buttons");
		frm.set_df_property("items", "cannot_add_rows", true);
	},

	set_query_filters(frm) {
		frm.set_query("parent_warehouse", (doc) => {
			return {
				filters: {
					is_group: 1,
					company: doc.company,
				},
			};
		});

		frm.set_query("item_code", "items", () => {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 1,
				},
			};
		});
	},

	generate_demand(frm) {
		frm.call({
			method: "generate_demand",
			doc: frm.doc,
			freeze: true,
			callback: function (r) {
				frm.reload_doc();
			},
		});
	},

	set_custom_buttons(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Planned") {
			frm.add_custom_button(__("Create MPS"), () => {
				frappe.model.open_mapped_doc({
					method: "erpnext.manufacturing.doctype.sales_forecast.sales_forecast.create_mps",
					frm: frm,
				});
			}).addClass("btn-primary");
		}
	},
});

frappe.ui.form.on("Sales Forecast Item", {
	adjust_qty(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.demand_qty = row.forecast_qty + row.adjust_qty;
		frappe.model.set_value(cdt, cdn, "demand_qty", row.demand_qty);
	},
});
