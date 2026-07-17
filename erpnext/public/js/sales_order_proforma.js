// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		erpnext.proforma.toggle_tab(frm, false);
		if (frm.doc.docstatus !== 1) return;

		frappe.db.get_single_value("Selling Settings", "enable_proforma_invoice").then((enabled) => {
			if (!enabled) return;

			frm.add_custom_button(
				__("Proforma Invoice"),
				() => erpnext.proforma.open_dialog(frm),
				__("Create")
			);
			erpnext.proforma.render_list(frm);
		});
	},
});

frappe.provide("erpnext.proforma");

Object.assign(erpnext.proforma, {
	toggle_tab(frm, show) {
		// Toggle the Tab Break itself: set_df_property refreshes the field control but not the
		// tab link, so drive the Tab object directly to actually show/hide the tab.
		const tab = frm.get_field("proforma_html")?.tab;
		if (tab) {
			tab.df.hidden = show ? 0 : 1;
			tab.toggle(show);
		} else {
			frm.set_df_property("proforma_tab", "hidden", show ? 0 : 1);
		}
	},

	open_dialog(frm) {
		frappe.call({
			method: "erpnext.selling.doctype.proforma_invoice.proforma_invoice.get_sales_order_items",
			args: { sales_order: frm.doc.name },
			callback: (r) => this.show_dialog(frm, r.message || []),
		});
	},

	show_dialog(frm, so_items) {
		frappe.model.with_doctype("Proforma Invoice", () => {
			const series = frappe.meta.get_docfield("Proforma Invoice", "naming_series");
			frappe.db
				.get_single_value("Selling Settings", "default_proforma_print_format")
				.then((default_print_format) => {
					this.build_dialog(frm, so_items, series ? series.options : "", default_print_format);
				});
		});
	},

	build_dialog(frm, so_items, series_options, default_print_format) {
		const dialog = new frappe.ui.Dialog({
			title: __("Create Proforma Invoice"),
			size: "large",
			fields: [
				{
					fieldname: "naming_series",
					fieldtype: "Select",
					label: __("Series"),
					options: series_options,
					default: (series_options || "").split("\n")[0],
					reqd: 1,
				},
				{ fieldname: "cb_series", fieldtype: "Column Break" },
				{
					fieldname: "print_format",
					fieldtype: "Link",
					label: __("Print Format"),
					options: "Print Format",
					default: default_print_format,
					get_query: () => ({ filters: { doc_type: "Sales Order" } }),
				},
				{
					fieldname: "letter_head",
					fieldtype: "Link",
					label: __("Letter Head"),
					options: "Letter Head",
				},
				{ fieldname: "items_section", fieldtype: "Section Break", label: __("Items") },
				{
					fieldname: "items",
					fieldtype: "Table",
					cannot_add_rows: true,
					data: so_items.map((row) => ({ ...row })),
					fields: [
						{
							fieldname: "item_code",
							fieldtype: "Data",
							label: __("Item"),
							read_only: 1,
							in_list_view: 1,
						},
						{
							fieldname: "qty",
							fieldtype: "Float",
							label: __("Qty"),
							in_list_view: 1,
						},
						{ fieldname: "item_name", fieldtype: "Data", hidden: 1 },
						{ fieldname: "so_detail", fieldtype: "Data", hidden: 1 },
					],
				},
			],
			primary_action_label: __("Create"),
			primary_action: (values) => this.create(frm, dialog, values),
		});

		dialog.show();
	},

	create(frm, dialog, values) {
		const items = (values.items || [])
			.filter((row) => flt(row.qty) > 0)
			.map((row) => ({ so_detail: row.so_detail, qty: row.qty }));

		if (!items.length) {
			frappe.msgprint(__("Please enter a quantity for at least one item."));
			return;
		}

		frappe.call({
			method: "erpnext.selling.doctype.proforma_invoice.proforma_invoice.make_proforma_invoice",
			args: {
				sales_order: frm.doc.name,
				items: JSON.stringify(items),
				naming_series: values.naming_series,
				print_format: values.print_format,
				letter_head: values.letter_head,
			},
			freeze: true,
			freeze_message: __("Creating Proforma Invoice..."),
			callback: (r) => {
				if (!r.message) return;
				dialog.hide();
				frappe.show_alert({
					message: __("Proforma Invoice {0} created", [r.message]),
					indicator: "green",
				});
				frm.reload_doc();
			},
		});
	},

	render_list(frm) {
		// EmbeddedList is a lazy bundle (not on the eager desk bundle), so pull it in first.
		frappe.require("embedded_list.bundle.js", () => this.build_list(frm));
	},

	build_list(frm) {
		const wrapper = frm.get_field("proforma_html").$wrapper.empty();
		const list = new frappe.ui.EmbeddedList({
			wrapper,
			doctype: "Proforma Invoice",
			filters: { sales_order: frm.doc.name, docstatus: 1 },
			fields: ["name", "proforma_date", "grand_total", "status", "proforma_pdf", "sent_on", "currency"],
			order_by: "creation desc",
			empty_message: __("No proforma invoices yet."),
			// Show the Proforma tab only once at least one proforma exists for this order.
			after_render() {
				erpnext.proforma.toggle_tab(frm, (this._all_data || []).length > 0);
			},
			columns: [
				{
					label: __("Proforma No"),
					type: "link",
					fieldname: "name",
					route: (row) => ["Form", "Proforma Invoice", row.name],
				},
				{
					label: __("Date"),
					fieldname: "proforma_date",
					render: (row) => frappe.datetime.str_to_user(row.proforma_date),
				},
				{
					label: __("Grand Total"),
					fieldname: "grand_total",
					render: (row) => format_currency(row.grand_total, row.currency),
				},
				{
					label: __("Status"),
					type: "badge",
					fieldname: "status",
					color: (row) => (row.status === "Issued" ? "green" : "gray"),
				},
				{
					type: "actions",
					actions: [
						{
							icon: "printer",
							label: __("View PDF"),
							action: (row) => row.proforma_pdf && window.open(row.proforma_pdf, "_blank"),
						},
						{
							icon: "mail",
							label: __("Send Email"),
							action: (row, refresh) => this.send_email(frm, row.name, refresh),
						},
					],
				},
			],
		});
		list.refresh();
	},

	send_email(frm, proforma_name, refresh) {
		frappe.prompt(
			[
				{
					fieldname: "recipients",
					fieldtype: "Data",
					label: __("Recipients"),
					reqd: 1,
					default: frm.doc.contact_email,
					description: __("Comma separated email addresses"),
				},
			],
			(values) => {
				frappe.call({
					method: "erpnext.selling.doctype.proforma_invoice.proforma_invoice.send_proforma_email",
					args: { proforma_name, recipients: values.recipients },
					freeze: true,
					callback: () => {
						frappe.show_alert({ message: __("Proforma emailed"), indicator: "green" });
						(refresh || (() => this.render_list(frm)))();
					},
				});
			},
			__("Send Proforma Invoice"),
			__("Send")
		);
	},
});
