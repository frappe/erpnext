// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.StockController = class StockController extends frappe.ui.form.Controller {
	onload() {
		// warehouse query if company
		if (this.frm.fields_dict.company) {
			this.setup_warehouse_query();
		}
	}

	setup_warehouse_query() {
		var me = this;
		erpnext.queries.setup_queries(this.frm, "Warehouse", function() {
			return erpnext.queries.warehouse(me.frm.doc);
		});
	}

	setup_posting_date_time_check() {
		// make posting date default and read only unless explictly checked
		frappe.ui.form.on(this.frm.doctype, 'set_posting_date_and_time_read_only', function(frm) {
			if(frm.doc.docstatus == 0 && frm.doc.set_posting_time) {
				frm.set_df_property('posting_date', 'read_only', 0);
				frm.set_df_property('posting_time', 'read_only', 0);
			} else {
				frm.set_df_property('posting_date', 'read_only', 1);
				frm.set_df_property('posting_time', 'read_only', 1);
			}
		})

		frappe.ui.form.on(this.frm.doctype, 'set_posting_time', function(frm) {
			frm.trigger('set_posting_date_and_time_read_only');
		});

		frappe.ui.form.on(this.frm.doctype, 'refresh', function(frm) {
			// set default posting date / time
			if(frm.doc.docstatus==0) {
				if(!frm.doc.posting_date) {
					frm.set_value('posting_date', frappe.datetime.nowdate());
				}
				if(!frm.doc.posting_time) {
					frm.set_value('posting_time', frappe.datetime.now_time());
				}
				frm.trigger('set_posting_date_and_time_read_only');
			}
		});
	}

	show_stock_ledger() {
		var me = this;
		if(this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: moment(me.frm.doc.modified).format('YYYY-MM-DD'),
					company: me.frm.doc.company,
					show_cancelled_entries: me.frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));
		}

	}

	show_general_ledger() {
		let me = this;
		if(this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: moment(me.frm.doc.modified).format('YYYY-MM-DD'),
					company: me.frm.doc.company,
					group_by: "Group by Voucher (Consolidated)",
					show_cancelled_entries: me.frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	}

	show_ledger_preview() {
		let me = this
		if(this.frm.doc.docstatus == 0) {
			cur_frm.add_custom_button(__('Accounting Ledger Preview'), function() {
				frappe.call({
					"method": "erpnext.controllers.stock_controller.show_ledger_preview",
					"args": {
						"company": me.frm.doc.company,
						"doctype": me.frm.doc.doctype,
						"docname": me.frm.doc.name
					},
					"callback": function(response) {
						me.get_datatable(response.message.gl_columns, response.message.gl_data, me.frm.get_field("accounting_ledger_preview_html").wrapper);
						me.get_datatable(response.message.sl_columns, response.message.sl_data, me.frm.get_field("stock_ledger_preview_html").wrapper);
						me.frm.scroll_to_field("accounting_ledger_preview_html");
					}
				})
			}, __("View"));
		}
	}

	get_datatable(columns, data, wrapper) {
		const datatable_options = {
			columns: columns,
			data: data,
			dynamicRowHeight: true,
			checkboxColumn: false,
			inlineFilters: true,
		};

		new frappe.DataTable(
			wrapper,
			datatable_options
		);
	}
};
