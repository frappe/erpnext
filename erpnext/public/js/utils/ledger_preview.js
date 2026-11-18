frappe.provide("erpnext.accounts");

erpnext.accounts.ledger_preview = {
	show_accounting_ledger_preview(frm) {
		let me = this;
		if (!frm.is_new() && frm.doc.docstatus == 0 && frappe.model.can_read("GL Entry")) {
			frm.add_custom_button(
				__("Accounting Ledger"),
				function () {
					frappe.call({
						type: "GET",
						method: "erpnext.controllers.stock_controller.show_accounting_ledger_preview",
						args: {
							company: frm.doc.company,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
						},
						callback: function (response) {
							me.make_dialog(
								"Accounting Ledger Preview",
								"accounting_ledger_preview_html",
								response.message.gl_columns,
								response.message.gl_data
							);
						},
					});
				},
				__("Preview")
			);
		}
	},

	show_stock_ledger_preview(frm) {
		let me = this;
		if (!frm.is_new() && frm.doc.docstatus == 0 && frappe.model.can_read("Stock Ledger Entry")) {
			frm.add_custom_button(
				__("Stock Ledger"),
				function () {
					frappe.call({
						type: "GET",
						method: "erpnext.controllers.stock_controller.show_stock_ledger_preview",
						args: {
							company: frm.doc.company,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
						},
						callback: function (response) {
							me.make_dialog(
								"Stock Ledger Preview",
								"stock_ledger_preview_html",
								response.message.sl_columns,
								response.message.sl_data
							);
						},
					});
				},
				__("Preview")
			);
		}
	},

	show_payment_ledger_preview(frm) {
		let me = this;
		if (!frm.is_new() && frm.doc.docstatus == 0 && frappe.model.can_read("Payment Ledger Entry")) {
			frm.add_custom_button(
				__("Payment Ledger"),
				function () {
					frappe.call({
						type: "GET",
						method: "erpnext.controllers.stock_controller.show_payment_ledger_preview",
						args: {
							company: frm.doc.company,
							doctype: frm.doc.doctype,
							docname: frm.doc.name,
						},
						callback: function (response) {
							me.make_dialog(
								"Payment Ledger Preview",
								"payment_ledger_preview_html",
								response.message.pl_columns,
								response.message.pl_data
							);
						},
					});
				},
				__("Preview")
			);
		}
	},

	make_dialog(label, fieldname, columns, data) {
		const no_impact_messages = {
			accounting_ledger_preview_html: __("No Impact on Accounting Ledger"),
			payment_ledger_preview_html: __("No Impact on Payment Ledger"),
		};

		if (data.length === 0 && no_impact_messages[fieldname]) {
			frappe.msgprint("<strong>" + no_impact_messages[fieldname] + "</strong>");
		} else {
			let me = this;
			let dialog = new frappe.ui.Dialog({
				size: "extra-large",
				title: __(label),
				fields: [
					{
						fieldtype: "HTML",
						fieldname: fieldname,
					},
				],
			});

			setTimeout(function () {
				me.get_datatable(columns, data, dialog.get_field(fieldname).wrapper);
			}, 200);

			dialog.show();
		}
	},

	get_datatable(columns, data, wrapper) {
		columns.forEach((col) => {
			if (col.fieldtype === "Currency") {
				col.format = (value) => {
					return format_currency(value, col.options);
				};
			}
		});

		const datatable_options = {
			columns: columns,
			data: data,
			dynamicRowHeight: true,
			checkboxColumn: false,
			inlineFilters: true,
		};

		new frappe.DataTable(wrapper, datatable_options);
	},
};
