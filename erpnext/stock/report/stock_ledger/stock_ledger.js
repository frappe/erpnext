// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Stock Ledger"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"qty_field",
			"label": __("Stock Qty or Contents Qty"),
			"fieldtype": "Select",
			"options": "Stock Qty\nContents Qty",
			"default": "Stock Qty"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {'include_disabled': 1}
				}
			},
			on_change: function() {
				var item_code = frappe.query_report.get_filter_value('item_code');
				if(!item_code) {
					frappe.query_report.set_filter_value('item_name', "");
				} else {
					frappe.db.get_value("Item", item_code, 'item_name', function(value) {
						frappe.query_report.set_filter_value('item_name', value['item_name']);
					});
				}
			}
		},
		{
			"fieldname":"item_name",
			"label": __("Item Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname":"batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options": "Batch"
		},
		{
			"fieldname":"brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand"
		},
		{
			fieldname: "item_source",
			label: __("Item Source"),
			fieldtype: "Link",
			options: "Item Source"
		},
		{
			"fieldname":"voucher_no",
			"label": __("Voucher #"),
			"fieldtype": "Data"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname":"include_uom",
			"label": __("Include UOM"),
			"fieldtype": "Link",
			"options": "UOM"
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type"
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			on_change: function() {
				var party_type = frappe.query_report.get_filter_value('party_type');
				var party = frappe.query_report.get_filter_value('party');

				if(!party_type || !party) {
					frappe.query_report.set_filter_value('party_name', "");
				} else {
					var fieldname = erpnext.utils.get_party_name(party_type) || "name";
					frappe.db.get_value(party_type, party, fieldname, function(value) {
						frappe.query_report.set_filter_value('party_name', value[fieldname]);
					});
				}
			}
		},
		{
			"fieldname":"party_name",
			"label": __("Party Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Ungrouped\nGroup by Item-Warehouse\nGroup by Item\nGroup by Warehouse\nGroup by Item Group\nGroup by Brand\nGroup by Party\nGroup by Voucher",
			"default": "Group by Item-Warehouse"
		},
		{
			"fieldname":"show_amounts_in_print",
			"label": __("Print with Amounts"),
			"fieldtype": "Check",
			"default": 0,
			on_change: function() { return false; }
		}
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (['actual_qty', 'stock_value_difference'].includes(column.fieldname)) {
			if (flt(value) > 0) {
				style['color'] = 'green';
			} else if (flt(value) < 0) {
				style['color'] = 'red';
			}
		}
		if (['qty_after_transaction', 'stock_value', 'valuation_rate'].includes(column.fieldname)) {
			if (flt(value) < 0) {
				style['background-color'] = 'pink';
				style['font-weight'] = 'bold';
			}
		}
		if (column.fieldname == 'qty_after_transaction' && !flt(value)) {
			style['color'] = '#00009a';
		}

		return default_formatter(value, row, column, data, {css: style});
	},
}

// $(function() {
// 	$(wrapper).bind("show", function() {
// 		frappe.query_report.load();
// 	});
// });
