// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Master Production Schedule", {
	refresh(frm) {
		frm.trigger("set_query_filters");

		frm.set_df_property("items", "cannot_add_rows", true);
		frm.set_df_property("material_requests", "cannot_add_rows", true);
		frm.set_df_property("sales_orders", "cannot_add_rows", true);
		frm.fields_dict.items.$wrapper.find("[data-action='duplicate_rows']").css("display", "none");

		frm.trigger("set_custom_buttons");
	},

	setup(frm) {
		frm.trigger("set_indicator_for_item");
	},

	set_indicator_for_item(frm) {
		frm.set_indicator_formatter("item_code", function (doc) {
			if (doc.order_release_date < frappe.datetime.get_today()) {
				return "orange";
			} else if (doc.order_release_date > frappe.datetime.get_today()) {
				return "blue";
			} else {
				return "green";
			}
		});
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

		frm.set_query("sales_forecast", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});
	},

	get_actual_demand(frm) {
		frm.call({
			method: "get_actual_demand",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Generating Master Production Schedule..."),
			callback: (r) => {
				frm.reload_doc();
			},
		});
	},

	set_custom_buttons(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View MRP"), () => {
				if (!frm.doc.items?.length && !frm.doc.sales_forecast) {
					frappe.throw(
						__(
							"Please set actual demand or sales forecast to generate Material Requirements Planning Report."
						)
					);
					return;
				}

				frappe.set_route("query-report", "Material Requirements Planning Report", {
					company: frm.doc.company,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					mps: frm.doc.name,
					warehouse: frm.doc.parent_warehouse,
					sales_forecast: frm.doc.sales_forecast,
				});
			});
		}
	},

	get_sales_orders(frm) {
		frm.sales_order_dialog = new frappe.ui.Dialog({
			fields: [
				{
					fieldtype: "Section Break",
					label: __("Filters for Sales Orders"),
				},
				{
					fieldname: "customer",
					fieldtype: "Link",
					options: "Customer",
					label: __("Customer"),
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "from_date",
					fieldtype: "Date",
					label: __("From Date"),
				},
				{
					fieldname: "to_date",
					fieldtype: "Date",
					label: __("To Date"),
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "delivery_from_date",
					fieldtype: "Date",
					label: __("Delivery From Date"),
					default: frm.doc.from_date,
				},
				{
					fieldname: "delivery_to_date",
					fieldtype: "Date",
					label: __("Delivery To Date"),
				},
			],
			title: __("Get Sales Orders"),
			size: "large",
			primary_action_label: __("Get Sales Orders"),
			primary_action: (data) => {
				frm.sales_order_dialog.hide();
				frm.events.fetch_sales_orders(frm, data);
			},
		});

		frm.sales_order_dialog.show();
	},

	fetch_sales_orders(frm, data) {
		frm.call({
			method: "fetch_sales_orders",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Fetching Sales Orders..."),
			args: data,
			callback: (r) => {
				frm.reload_doc();
			},
		});
	},

	get_material_requests(frm) {
		frm.sales_order_dialog = new frappe.ui.Dialog({
			fields: [
				{
					fieldtype: "Section Break",
					label: __("Filters for Material Requests"),
				},
				{
					fieldname: "material_request_type",
					fieldtype: "Select",
					label: __("Purpose"),
					options: "\nPurchase\nManufacture",
					default: "Manufacture",
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "from_date",
					fieldtype: "Date",
					label: __("From Date"),
				},
				{
					fieldname: "to_date",
					fieldtype: "Date",
					label: __("To Date"),
				},
			],
			title: __("Get Material Requests"),
			size: "large",
			primary_action_label: __("Get Material Requests"),
			primary_action: (data) => {
				frm.sales_order_dialog.hide();
				frm.events.fetch_materials_requests(frm, data);
			},
		});

		frm.sales_order_dialog.show();
	},

	fetch_materials_requests(frm, data) {
		frm.call({
			method: "fetch_materials_requests",
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Fetching Material Requests..."),
			args: data,
			callback: (r) => {
				frm.reload_doc();
			},
		});
	},
});
