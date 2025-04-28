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

<<<<<<< HEAD
	barcode(doc, cdt, cdn) {
=======
	barcode(doc, cdt, cdn)  {
>>>>>>> 7c4cf3e834 (Favicon.svg)
		let row = locals[cdt][cdn];
		if (row.barcode) {
			erpnext.stock.utils.set_item_details_using_barcode(this.frm, row, (r) => {
				frappe.model.set_value(cdt, cdn, {
<<<<<<< HEAD
					item_code: r.message.item_code,
					qty: 1,
=======
					"item_code": r.message.item_code,
					"qty": 1,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				});
			});
		}
	}

	setup_warehouse_query() {
		var me = this;
<<<<<<< HEAD
		erpnext.queries.setup_queries(this.frm, "Warehouse", function () {
=======
		erpnext.queries.setup_queries(this.frm, "Warehouse", function() {
>>>>>>> 7c4cf3e834 (Favicon.svg)
			return erpnext.queries.warehouse(me.frm.doc);
		});
	}

	setup_posting_date_time_check() {
		// make posting date default and read only unless explictly checked
<<<<<<< HEAD
		frappe.ui.form.on(this.frm.doctype, "set_posting_date_and_time_read_only", function (frm) {
			if (frm.doc.docstatus == 0 && frm.doc.set_posting_time) {
				frm.set_df_property("posting_date", "read_only", 0);
				frm.set_df_property("posting_time", "read_only", 0);
			} else {
				frm.set_df_property("posting_date", "read_only", 1);
				frm.set_df_property("posting_time", "read_only", 1);
			}
		});

		frappe.ui.form.on(this.frm.doctype, "set_posting_time", function (frm) {
			frm.trigger("set_posting_date_and_time_read_only");
		});

		frappe.ui.form.on(this.frm.doctype, "refresh", function (frm) {
			// set default posting date / time
			if (frm.doc.docstatus == 0) {
				if (!frm.doc.posting_date) {
					frm.set_value("posting_date", frappe.datetime.nowdate());
				}
				if (!frm.doc.posting_time) {
					frm.set_value("posting_time", frappe.datetime.now_time());
				}
				frm.trigger("set_posting_date_and_time_read_only");
=======
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
>>>>>>> 7c4cf3e834 (Favicon.svg)
			}
		});
	}

	show_stock_ledger() {
		var me = this;
<<<<<<< HEAD
		if (this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(
				__("Stock Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: me.frm.doc.name,
						from_date: me.frm.doc.posting_date,
						to_date: moment(me.frm.doc.modified).format("YYYY-MM-DD"),
						company: me.frm.doc.company,
						show_cancelled_entries: me.frm.doc.docstatus === 2,
						ignore_prepared_report: true,
					};
					frappe.set_route("query-report", "Stock Ledger");
				},
				__("View")
			);
		}
=======
		if(this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: moment(me.frm.doc.modified).format('YYYY-MM-DD'),
					company: me.frm.doc.company,
					show_cancelled_entries: me.frm.doc.docstatus === 2,
					ignore_prepared_report: true
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));
		}

>>>>>>> 7c4cf3e834 (Favicon.svg)
	}

	show_general_ledger() {
		let me = this;
<<<<<<< HEAD
		if (this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(
				__("Accounting Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: me.frm.doc.name,
						from_date: me.frm.doc.posting_date,
						to_date: moment(me.frm.doc.modified).format("YYYY-MM-DD"),
						company: me.frm.doc.company,
						categorize_by: "Categorize by Voucher (Consolidated)",
						show_cancelled_entries: me.frm.doc.docstatus === 2,
						ignore_prepared_report: true,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);
=======
		if(this.frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: moment(me.frm.doc.modified).format('YYYY-MM-DD'),
					company: me.frm.doc.company,
					group_by: "Group by Voucher (Consolidated)",
					show_cancelled_entries: me.frm.doc.docstatus === 2,
					ignore_prepared_report: true
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
>>>>>>> 7c4cf3e834 (Favicon.svg)
		}
	}
};
