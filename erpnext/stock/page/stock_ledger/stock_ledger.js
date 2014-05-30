// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['stock-ledger'].onload = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Ledger'),
		single_column: true
	});

	new erpnext.StockLedger(wrapper);
	wrapper.appframe.add_module_icon("Stock")
}

frappe.require("assets/erpnext/js/stock_grid_report.js");

erpnext.StockLedger = erpnext.StockGridReport.extend({
	init: function(wrapper) {
		this._super({
			title: __("Stock Ledger"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Item", "Item Group", "Warehouse", "Stock Ledger Entry", "Brand", "Serial No"],
		})
	},

	setup_columns: function() {
		this.hide_balance = (this.is_default("item_code") || this.voucher_no) ? true : false;
		this.columns = [
			{id: "posting_datetime", name: __("Posting Date"), field: "posting_datetime", width: 120,
				formatter: this.date_formatter},
			{id: "item_code", name: __("Item Code"), field: "item_code", width: 160,
				link_formatter: {
					filter_input: "item_code",
					open_btn: true,
					doctype: '"Item"',
				}},
			{id: "description", name: __("Description"), field: "description", width: 200,
				formatter: this.text_formatter},
			{id: "warehouse", name: __("Warehouse"), field: "warehouse", width: 100,
				link_formatter: {filter_input: "warehouse"}},
			{id: "brand", name: __("Brand"), field: "brand", width: 100},
			{id: "stock_uom", name: __("UOM"), field: "stock_uom", width: 100},
			{id: "qty", name: __("Qty"), field: "qty", width: 100,
				formatter: this.currency_formatter},
			{id: "balance", name: __("Balance Qty"), field: "balance", width: 100,
				formatter: this.currency_formatter,
				hidden: this.hide_balance},
			{id: "balance_value", name: __("Balance Value"), field: "balance_value", width: 100,
				formatter: this.currency_formatter, hidden: this.hide_balance},
			{id: "voucher_type", name: __("Voucher Type"), field: "voucher_type", width: 120},
			{id: "voucher_no", name: __("Voucher No"), field: "voucher_no", width: 160,
				link_formatter: {
					filter_input: "voucher_no",
					open_btn: true,
					doctype: "dataContext.voucher_type"
				}},
		];

	},
	filters: [
		{fieldtype:"Select", label: __("Warehouse"), link:"Warehouse",
			default_value: "Select Warehouse...", filter: function(val, item, opts) {
				return item.warehouse == val || val == opts.default_value;
			}},
		{fieldtype:"Link", label: __("Item Code"), link:"Item", default_value: "Select Item...",
			filter: function(val, item, opts) {
				return item.item_code == val || !val;
			}},
		{fieldtype:"Select", label: "Brand", link:"Brand",
			default_value: "Select Brand...", filter: function(val, item, opts) {
				return val == opts.default_value || item.brand == val || item._show;
			}, link_formatter: {filter_input: "brand"}},
		{fieldtype:"Data", label: __("Voucher No"),
			filter: function(val, item, opts) {
				if(!val) return true;
				return (item.voucher_no && item.voucher_no.indexOf(val)!=-1);
			}},
		{fieldtype:"Date", label: __("From Date"), filter: function(val, item) {
			return dateutil.str_to_obj(val) <= dateutil.str_to_obj(item.posting_date);
		}},
		{fieldtype:"Label", label: __("To")},
		{fieldtype:"Date", label: __("To Date"), filter: function(val, item) {
			return dateutil.str_to_obj(val) >= dateutil.str_to_obj(item.posting_date);
		}},
		{fieldtype:"Button", label: __("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: __("Reset Filters"), icon: "icon-filter"}
	],

	setup_filters: function() {
		var me = this;
		this._super();

		this.wrapper.bind("apply_filters_from_route", function() { me.toggle_enable_brand(); });
		this.filter_inputs.item_code.change(function() { me.toggle_enable_brand(); });

		this.trigger_refresh_on_change(["item_code", "warehouse", "brand"]);
	},

	toggle_enable_brand: function() {
		if(!this.filter_inputs.item_code.val()) {
			this.filter_inputs.brand.prop("disabled", false);
		} else {
			this.filter_inputs.brand
				.val(this.filter_inputs.brand.get(0).opts.default_value)
				.prop("disabled", true);
		}
	},

	init_filter_values: function() {
		this._super();
		this.filter_inputs.warehouse.get(0).selectedIndex = 0;
	},
	prepare_data: function() {
		var me = this;
		if(!this.item_by_name)
			this.item_by_name = this.make_name_map(frappe.report_dump.data["Item"]);
		var data = frappe.report_dump.data["Stock Ledger Entry"];
		var out = [];

		var opening = {
			item_code: "On " + dateutil.str_to_user(this.from_date), qty: 0.0, balance: 0.0,
				id:"_opening", _show: true, _style: "font-weight: bold", balance_value: 0.0
		}
		var total_in = {
			item_code: "Total In", qty: 0.0, balance: 0.0, balance_value: 0.0,
				id:"_total_in", _show: true, _style: "font-weight: bold"
		}
		var total_out = {
			item_code: "Total Out", qty: 0.0, balance: 0.0, balance_value: 0.0,
				id:"_total_out", _show: true, _style: "font-weight: bold"
		}

		// clear balance
		$.each(frappe.report_dump.data["Item"], function(i, item) {
			item.balance = item.balance_value = 0.0;
		});

		// initialize warehouse-item map
		this.item_warehouse = {};
		this.serialized_buying_rates = this.get_serialized_buying_rates();
		var from_datetime = dateutil.str_to_obj(me.from_date + " 00:00:00");
		var to_datetime = dateutil.str_to_obj(me.to_date + " 23:59:59");

		//
		for(var i=0, j=data.length; i<j; i++) {
			var sl = data[i];
			var item = me.item_by_name[sl.item_code]
			var wh = me.get_item_warehouse(sl.warehouse, sl.item_code);
			sl.description = item.description;
			sl.posting_datetime = sl.posting_date + " " + (sl.posting_time || "00:00:00");
			sl.brand = item.brand;
			var posting_datetime = dateutil.str_to_obj(sl.posting_datetime);

			var is_fifo = item.valuation_method ? item.valuation_method=="FIFO"
				: sys_defaults.valuation_method=="FIFO";
			var value_diff = me.get_value_diff(wh, sl, is_fifo);

			// opening, transactions, closing, total in, total out
			var before_end = posting_datetime <= to_datetime;
			if((!me.is_default("item_code") ? me.apply_filter(sl, "item_code") : true)
				&& me.apply_filter(sl, "warehouse") && me.apply_filter(sl, "voucher_no")
				&& me.apply_filter(sl, "brand")) {
				if(posting_datetime < from_datetime) {
					opening.balance += sl.qty;
					opening.balance_value += value_diff;
				} else if(before_end) {
					if(sl.qty > 0) {
						total_in.qty += sl.qty;
						total_in.balance_value += value_diff;
					} else {
						total_out.qty += (-1 * sl.qty);
						total_out.balance_value += value_diff;
					}
				}
			}

			if(!before_end) break;

			// apply filters
			if(me.apply_filters(sl)) {
				out.push(sl);
			}

			// update balance
			if((!me.is_default("warehouse") ? me.apply_filter(sl, "warehouse") : true)) {
				sl.balance = me.item_by_name[sl.item_code].balance + sl.qty;
				me.item_by_name[sl.item_code].balance = sl.balance;

				sl.balance_value = me.item_by_name[sl.item_code].balance_value + value_diff;
				me.item_by_name[sl.item_code].balance_value = sl.balance_value;
			}
		}

		if(me.item_code && !me.voucher_no) {
			var closing = {
				item_code: "On " + dateutil.str_to_user(this.to_date),
				balance: (out.length ? out[out.length-1].balance : 0), qty: 0,
				balance_value: (out.length ? out[out.length-1].balance_value : 0),
				id:"_closing", _show: true, _style: "font-weight: bold"
			};
			total_out.balance_value = -total_out.balance_value;
			var out = [opening].concat(out).concat([total_in, total_out, closing]);
		}

		this.data = out;
	},
	get_plot_data: function() {
		var data = [];
		var me = this;
		if(me.hide_balance) return false;
		data.push({
			label: me.item_code,
			data: [[dateutil.str_to_obj(me.from_date).getTime(), me.data[0].balance]]
				.concat($.map(me.data, function(col, idx) {
					if (col.posting_datetime) {
						return [[dateutil.str_to_obj(col.posting_datetime).getTime(), col.balance - col.qty],
								[dateutil.str_to_obj(col.posting_datetime).getTime(), col.balance]]
					}
					return null;
				})).concat([
					// closing
					[dateutil.str_to_obj(me.to_date).getTime(), me.data[me.data.length - 1].balance]
				]),
			points: {show: true},
			lines: {show: true, fill: true},
		});
		return data;
	},
	get_plot_options: function() {
		return {
			grid: { hoverable: true, clickable: true },
			xaxis: { mode: "time",
				min: dateutil.str_to_obj(this.from_date).getTime(),
				max: dateutil.str_to_obj(this.to_date).getTime(),
			},
			series: { downsample: { threshold: 1000 } }
		}
	},
	get_tooltip_text: function(label, x, y) {
		var d = new Date(x);
		var date = dateutil.obj_to_user(d) + " " + d.getHours() + ":" + d.getMinutes();
	 	var value = format_number(y);
		return value.bold() + " on " + date;
	}
});
