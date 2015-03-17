// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");

erpnext.stock.StockController = frappe.ui.form.Controller.extend({
	onload: function() {
		// warehouse query if company
		if (this.frm.fields_dict.company) {
			this.setup_warehouse_query();
		}
	},

	setup_warehouse_query: function() {
		var me = this;
		var warehouse_query_method = function() {
			return erpnext.queries.warehouse(me.frm.doc);
		};

		var _set_warehouse_query = function(doctype, parentfield) {
			var warehouse_link_fields = frappe.meta.get_docfields(doctype, me.frm.doc.name,
				{"fieldtype": "Link", "options": "Warehouse"});
			$.each(warehouse_link_fields, function(i, df) {
				if(parentfield) {
					me.frm.set_query(df.fieldname, parentfield, warehouse_query_method);
				} else {
					me.frm.set_query(df.fieldname, warehouse_query_method);
				}
			});
		};

		_set_warehouse_query(me.frm.doc.doctype);

		// warehouse field in tables
		var table_fields = frappe.meta.get_docfields(me.frm.doc.doctype, me.frm.doc.name,
			{"fieldtype": "Table"});

		$.each(table_fields, function(i, df) {
			_set_warehouse_query(df.options, df.fieldname);
		});
	},

	show_stock_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, "icon-bar-chart");
		}

	},

	show_general_ledger: function() {
		var me = this;
		if(this.frm.doc.docstatus===1 && cint(frappe.defaults.get_default("auto_accounting_for_stock"))) {
			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: me.frm.doc.name,
					from_date: me.frm.doc.posting_date,
					to_date: me.frm.doc.posting_date,
					company: me.frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, "icon-table");
		}
	},

	copy_account_in_all_row: function(doc, dt, dn, fieldname) {
		var d = locals[dt][dn];
		if(d[fieldname]){
			var cl = doc["items"] || [];
			for(var i = 0; i < cl.length; i++) {
				if(!cl[i][fieldname]) cl[i][fieldname] = d[fieldname];
			}
		}
		refresh_field("items");
	}
});
