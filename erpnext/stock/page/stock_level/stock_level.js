// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['stock-level'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Stock Level'),
		single_column: true
	});

	new erpnext.StockLevel(wrapper);


	frappe.breadcrumbs.add("Stock")
	;
}

frappe.require("assets/erpnext/js/stock_grid_report.js");

erpnext.StockLevel = erpnext.StockGridReport.extend({
	init: function(wrapper) {
		var me = this;

		this._super({
			title: __("Stock Level"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Item", "Warehouse", "Stock Ledger Entry", "Production Order",
				"Material Request Item", "Purchase Order Item", "Sales Order Item", "Brand", "Serial No"],
		});

		this.wrapper.bind("make", function() {
			frappe.utils.set_footnote(me, me.wrapper.get(0),
				"<ul> \
					<li style='font-weight: bold;'> \
						Projected Qty = Actual Qty + Planned Qty + Requested Qty \
						+ Ordered Qty - Reserved Qty </li> \
					<ul> \
						<li>"+__("Actual Qty: Quantity available in the warehouse.") +"</li>"+
						"<li>"+__("Planned Qty: Quantity, for which, Production Order has been raised, but is pending to be manufactured.")+ "</li> " +
						"<li>"+__("Requested Qty: Quantity requested for purchase, but not ordered.") + "</li>" +
						"<li>" + __("Ordered Qty: Quantity ordered for purchase, but not received.")+ "</li>" +
						"<li>" + __("Reserved Qty: Quantity ordered for sale, but not delivered.") +  "</li>" +
					"</ul> \
				</ul>");
		});
	},

	setup_columns: function() {
		this.columns = [
			{id: "item_code", name: __("Item Code"), field: "item_code", width: 160,
				link_formatter: {
					filter_input: "item_code",
					open_btn: true,
					doctype: '"Item"',
				}},
			{id: "item_name", name: __("Item Name"), field: "item_name", width: 100,
				formatter: this.text_formatter},
			{id: "description", name: __("Description"), field: "description", width: 200,
				formatter: this.text_formatter},
			{id: "brand", name: __("Brand"), field: "brand", width: 100,
				link_formatter: {filter_input: "brand"}},
			{id: "warehouse", name: __("Warehouse"), field: "warehouse", width: 100,
				link_formatter: {filter_input: "warehouse"}},
			{id: "uom", name: __("UOM"), field: "uom", width: 60},
			{id: "actual_qty", name: __("Actual Qty"),
				field: "actual_qty", width: 80, formatter: this.currency_formatter},
			{id: "planned_qty", name: __("Planned Qty"),
				field: "planned_qty", width: 80, formatter: this.currency_formatter},
			{id: "requested_qty", name: __("Requested Qty"),
				field: "requested_qty", width: 80, formatter: this.currency_formatter},
			{id: "ordered_qty", name: __("Ordered Qty"),
				field: "ordered_qty", width: 80, formatter: this.currency_formatter},
			{id: "reserved_qty", name: __("Reserved Qty"),
				field: "reserved_qty", width: 80, formatter: this.currency_formatter},
			{id: "projected_qty", name: __("Projected Qty"),
				field: "projected_qty", width: 80, formatter: this.currency_formatter},
			{id: "re_order_level", name: __("Re-Order Level"),
				field: "re_order_level", width: 80, formatter: this.currency_formatter},
			{id: "re_order_qty", name: __("Re-Order Qty"),
				field: "re_order_qty", width: 80, formatter: this.currency_formatter},
		];
	},

	filters: [
		{fieldtype:"Link", label: __("Item Code"), link:"Item", default_value: "Select Item...",
			filter: function(val, item, opts) {
				return item.item_code == val || !val;
			}},

		{fieldtype:"Select", label: __("Warehouse"), link:"Warehouse",
			default_value: "Select Warehouse...", filter: function(val, item, opts) {
				return item.warehouse == val || val == opts.default_value;
			}},

		{fieldtype:"Select", label: __("Brand"), link:"Brand",
			default_value: "Select Brand...", filter: function(val, item, opts) {
				return val == opts.default_value || item.brand == val;
			}}
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

		if(!this._data) {
			this._data = [];
			this.item_warehouse_map = {};
			this.item_by_name = this.make_name_map(frappe.report_dump.data["Item"]);
			this.calculate_quantities();
		}

		this.data = [].concat(this._data);
		this.data = $.map(this.data, function(d) {
			return me.apply_filters(d) ? d : null;
		});

		this.calculate_total();
	},

	calculate_quantities: function() {
		var me = this;
		$.each([
			["Stock Ledger Entry", "actual_qty"],
			["Production Order", "planned_qty"],
			["Material Request Item", "requested_qty"],
			["Purchase Order Item", "ordered_qty"],
			["Sales Order Item", "reserved_qty"]],
			function(i, v) {
				$.each(frappe.report_dump.data[v[0]], function(i, item) {
					var row = me.get_row(item.item_code, item.warehouse);
					row[v[1]] += flt(item.qty);
				});
			}
		);

		// sort by item, warehouse
		this._data = $.map(Object.keys(this.item_warehouse_map).sort(), function(key) {
			return me.item_warehouse_map[key];
		});

		// calculate projected qty
		$.each(this._data, function(i, row) {
			row.projected_qty = row.actual_qty + row.planned_qty + row.requested_qty
				+ row.ordered_qty - row.reserved_qty;
		});

		// filter out rows with zero values
		this._data = $.map(this._data, function(d) {
			return me.apply_zero_filter(null, d, null, me) ? d : null;
		});
	},

	get_row: function(item_code, warehouse) {
		var key = item_code + ":" + warehouse;
		if(!this.item_warehouse_map[key]) {
			var item = this.item_by_name[item_code];
			var row = {
				item_code: item_code,
				warehouse: warehouse,
				description: item.description,
				brand: item.brand,
				item_name: item.item_name || item.name,
				uom: item.stock_uom,
				id: key,
			}
			this.reset_item_values(row);

			row["re_order_level"] = item.re_order_level
			row["re_order_qty"] = item.re_order_qty

			this.item_warehouse_map[key] = row;
		}
		return this.item_warehouse_map[key];
	},

	calculate_total: function() {
		var me = this;
		// show total if a specific item is selected and warehouse is not filtered
		if(this.is_default("warehouse") && !this.is_default("item_code")) {
			var total = {
				id: "_total",
				item_code: "Total",
				_style: "font-weight: bold",
				_show: true
			};
			this.reset_item_values(total);

			$.each(this.data, function(i, row) {
				$.each(me.columns, function(i, col) {
					if (col.formatter==me.currency_formatter) {
						total[col.id] += row[col.id];
					}
				});
			});

			this.data = this.data.concat([total]);
		}
	}
})
