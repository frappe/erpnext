// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		erpnext.proforma.toggle_tab(frm, false);
		if (frm.doc.docstatus !== 1) return;

		frappe.db.get_single_value("Selling Settings", "enable_proforma_invoice").then((enabled) => {
			if (!enabled) return;

			// Defer so the button lands after the standard Create options, not before them.
			setTimeout(() => {
				frm.add_custom_button(
					__("Proforma Invoice"),
					() => erpnext.proforma.open_dialog(frm),
					__("Create")
				);
			}, 0);
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
					fieldname: "based_on",
					fieldtype: "Select",
					label: __("Based On"),
					options: ["Quantity", "Amount"],
					default: "Quantity",
					onchange: () => this.toggle_basis(dialog),
				},
				{
					fieldname: "hide_item_qty",
					fieldtype: "Check",
					label: __("Hide Item Quantity in Print"),
					depends_on: 'eval:doc.based_on=="Amount"',
				},
				{
					fieldname: "items",
					fieldtype: "Table",
					cannot_add_rows: true,
					// Pre-fill the remaining (ordered minus already-proformed) for each basis.
					data: so_items.map((row) => ({
						...row,
						qty: Math.max(0, flt(row.qty) - flt(row.proformed_qty)),
						amount: Math.max(0, flt(row.amount) - flt(row.proformed_amount)),
					})),
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
							onchange: function () {
								// In Quantity basis, Amount is derived (qty x rate). Recompute across
								// all rows and re-render — refreshing a single row only updates the
								// active one, so rows beyond the edited one would go stale.
								if (dialog.get_value("based_on") === "Quantity") {
									const grid = dialog.get_field("items").grid;
									(grid.grid_rows || []).forEach((row) => {
										if (row.doc) row.doc.amount = flt(row.doc.qty) * flt(row.doc.rate);
									});
									grid.refresh();
								}
								erpnext.proforma.update_warning(dialog);
							},
						},
						{
							fieldname: "amount",
							fieldtype: "Currency",
							label: __("Amount"),
							in_list_view: 1,
							read_only: 1,
							onchange: () => this.update_warning(dialog),
						},
						{ fieldname: "item_name", fieldtype: "Data", hidden: 1 },
						{ fieldname: "rate", fieldtype: "Currency", hidden: 1 },
						{ fieldname: "so_detail", fieldtype: "Data", hidden: 1 },
					],
				},
				{ fieldname: "warning_html", fieldtype: "HTML" },
			],
			primary_action_label: __("Create"),
			primary_action: (values) => this.create(frm, dialog, values),
		});

		dialog._so_items = so_items;
		dialog.show();
		this.update_warning(dialog);
	},

	// Qty is always editable; Amount is editable only in Amount basis (else it is derived).
	toggle_basis(dialog) {
		const by_amount = dialog.get_value("based_on") === "Amount";
		const grid = dialog.get_field("items").grid;
		grid.toggle_enable("qty", true);
		grid.toggle_enable("amount", by_amount);
		this.update_warning(dialog);
	},

	// Non-blocking notice below the table: flag lines whose total proforma qty/amount (this
	// proforma plus already-issued ones) exceeds the ordered qty/amount for the chosen basis.
	update_warning(dialog) {
		const by_amount = dialog.get_value("based_on") === "Amount";
		const field = by_amount ? "amount" : "qty";
		const proformed_field = by_amount ? "proformed_amount" : "proformed_qty";
		const so_item = {};
		(dialog._so_items || []).forEach((row) => (so_item[row.so_detail] = row));

		const exceeded = [];
		(dialog.get_value("items") || []).forEach((row) => {
			const item = so_item[row.so_detail];
			if (!item) return;
			const ordered = flt(by_amount ? item.amount : item.qty);
			const total = flt(item[proformed_field]) + flt(row[field]);
			if (total > ordered + 0.0001) exceeded.push(item.item_code);
		});

		const $wrapper = dialog.get_field("warning_html").$wrapper;
		if (!exceeded.length) {
			$wrapper.empty();
			return;
		}
		const basis = by_amount ? __("amount") : __("quantity");
		$wrapper.html(
			`<div class="text-danger small" style="margin-top: 8px;">${__(
				"Total proforma {0} (including past proformas) exceeds the ordered {0} for: {1}",
				[basis, frappe.utils.escape_html(exceeded.join(", "))]
			)}</div>`
		);
	},

	create(frm, dialog, values) {
		const by_amount = values.based_on === "Amount";
		const items = (values.items || [])
			.filter((row) => flt(by_amount ? row.amount : row.qty) > 0)
			.map((row) =>
				by_amount
					? { so_detail: row.so_detail, qty: row.qty, amount: row.amount }
					: { so_detail: row.so_detail, qty: row.qty }
			);

		if (!items.length) {
			frappe.msgprint(__("Please enter a quantity or amount for at least one item."));
			return;
		}

		frappe.call({
			method: "erpnext.selling.doctype.proforma_invoice.proforma_invoice.make_proforma_invoice",
			args: {
				sales_order: frm.doc.name,
				items: JSON.stringify(items),
				based_on: values.based_on,
				hide_item_qty: values.hide_item_qty ? 1 : 0,
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
				// Open the Proforma tab once the reloaded form has rendered the list.
				frm._activate_proforma_tab = true;
				frm.reload_doc();
			},
		});
	},

	render_list(frm) {
		// EmbeddedList is a lazy bundle (not on the eager desk bundle), so pull it in first.
		frappe.require("embedded_list.bundle.js", () => this.build_list(frm));
	},

	build_list(frm) {
		const container = frm.get_field("proforma_html").$wrapper.empty();
		const list = new frappe.ui.EmbeddedList({
			wrapper: $("<div></div>").appendTo(container),
			doctype: "Proforma Invoice",
			// Include cancelled (docstatus 2) so voided proformas stay visible for audit.
			filters: { sales_order: frm.doc.name, docstatus: ["in", [1, 2]] },
			fields: ["name", "proforma_date", "grand_total", "status", "proforma_pdf", "sent_on", "currency"],
			order_by: "creation desc",
			empty_message: __("No proforma invoices yet."),
			// Show the Proforma tab only once at least one proforma exists for this order.
			after_render() {
				const has_proformas = (this._all_data || []).length > 0;
				erpnext.proforma.toggle_tab(frm, has_proformas);
				if (has_proformas && frm._activate_proforma_tab) {
					frm._activate_proforma_tab = false;
					frm.get_field("proforma_html")?.tab?.set_active();
				}
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
					color: (row) => (row.status === "Cancelled" ? "red" : "green"),
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
							action: (row, refresh) => {
								if (row.status === "Cancelled") {
									frappe.msgprint(__("A cancelled Proforma Invoice cannot be emailed."));
									return;
								}
								this.send_email(frm, row.name, refresh);
							},
						},
					],
				},
			],
		});
		list.refresh();

		frappe.ui
			.button({
				label: __("New Proforma Invoice"),
				icon: "plus",
				variant: "subtle",
				size: "sm",
				onclick: () => this.open_dialog(frm),
			})
			.appendTo(
				$('<div class="flex justify-end" style="margin: 10px 0 20px;"></div>').appendTo(container)
			);
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
