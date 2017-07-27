// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['sales-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Sales Analytics'),
		single_column: true
	});
	new erpnext.SalesAnalytics(wrapper);


	frappe.breadcrumbs.add("Selling")

};

erpnext.SalesAnalytics = frappe.views.TreeGridReport.extend({
	init: function(wrapper) {
		this._super({
			title: __("Sales Analytics"),
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Item", "Item Group", "Customer", "Customer Group", "Company", "Territory",
				"Fiscal Year", "Sales Invoice", "Sales Invoice Item",
				"Sales Order", "Sales Order Item[Sales Analytics]",
				"Delivery Note", "Delivery Note Item[Sales Analytics]"],
			tree_grid: { show: true }
		});

		this.tree_grids = {
			"Customer Group": {
				label: __("Customer Group / Customer"),
				show: true,
				item_key: "customer",
				parent_field: "parent_customer_group",
				formatter: function(item) {
					return item.customer_name? item.customer_name + " (" + item.name + ")" : item.name; 
				}
			},
			"Customer": {
				label: __("Customer"),
				show: false,
				item_key: "customer",
				formatter: function(item) {
					return item.customer_name? item.customer_name + " (" + item.name + ")" : item.name;
				}
			},
			"Item Group": {
				label: __("Item"),
				show: true,
				parent_field: "parent_item_group",
				item_key: "item_code",
				formatter: function(item) {
					return item.name;
				}
			},
			"Item": {
				label: __("Item"),
				show: false,
				item_key: "item_code",
				formatter: function(item) {
					return item.name;
				}
			},
			"Territory": {
				label: __("Territory / Customer"),
				show: true,
				item_key: "customer",
				parent_field: "parent_territory",
				formatter: function(item) {
					return item.customer_name? item.customer_name + " (" + item.name + ")" : item.name;
				}
			}
		}
	},
	setup_columns: function() {
		this.tree_grid = this.tree_grids[this.tree_type];

		var std_columns = [
			{id: "check", name: "Plot", field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: this.tree_grid.label, field: "name", width: 300,
				formatter: this.tree_formatter},
			{id: "total", name: "Total", field: "total", plot: false,
				formatter: this.currency_formatter}
		];

		this.make_date_range_columns();
		this.columns = std_columns.concat(this.columns);
	},
	filters: [
		{fieldtype:"Select", fieldname: "tree_type", label: __("Tree Type"), options:["Customer Group", "Customer",
			"Item Group", "Item", "Territory"],
			filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);
			}},
		{fieldtype:"Select", fieldname: "based_on", label: __("Based On"), options:["Sales Invoice",
			"Sales Order", "Delivery Note"]},
		{fieldtype:"Select", fieldname: "value_or_qty", label:  __("Value or Qty"),
			options:[{label: __("Value"), value: "Value"}, {label: __("Quantity"), value: "Quantity"}]},
		{fieldtype:"Date", fieldname: "from_date", label: __("From Date")},
		{fieldtype:"Label", fieldname: "to", label: __("To")},
		{fieldtype:"Date", fieldname: "to_date", label: __("To Date")},
		{fieldtype:"Select", fieldname: "company", label: __("Company"), link:"Company",
			default_value: __("Select Company...")},
		{fieldtype:"Select", label: __("Range"), fieldname: "range",
			options:[{label: __("Daily"), value: "Daily"}, {label: __("Weekly"), value: "Weekly"},
				{label: __("Monthly"), value: "Monthly"}, {label: __("Quarterly"), value: "Quarterly"},
				{label: __("Yearly"), value: "Yearly"}]}
	],
	setup_filters: function() {
		var me = this;
		this._super();

		this.trigger_refresh_on_change(["value_or_qty", "tree_type", "based_on", "company"]);

		this.show_zero_check()
		this.setup_chart_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Monthly');
	},
	prepare_data: function() {
		var me = this;
		if (!this.tl) {
			// add 'Not Set' Customer & Item
			// (Customer / Item are not mandatory!!)
			frappe.report_dump.data["Customer"].push({
				name: "Not Set",
				parent_customer_group: "All Customer Groups",
				parent_territory: "All Territories",
				id: "Not Set",
			});

			frappe.report_dump.data["Item"].push({
				name: "Not Set",
				parent_item_group: "All Item Groups",
				id: "Not Set",
			});
		}

		if (!this.tl || !this.tl[this.based_on]) {
			this.make_transaction_list(this.based_on, this.based_on + " Item");
		}

		if(!this.data || me.item_type != me.tree_type) {
			if(me.tree_type=='Customer') {
				var items = frappe.report_dump.data["Customer"];
			} if(me.tree_type=='Customer Group') {
				var items = this.prepare_tree("Customer", "Customer Group");
			} else if(me.tree_type=="Item Group") {
				var items = this.prepare_tree("Item", "Item Group");
			} else if(me.tree_type=="Item") {
				var items = frappe.report_dump.data["Item"];
			} else if(me.tree_type=="Territory") {
				var items = this.prepare_tree("Customer", "Territory");
			}

			me.item_type = me.tree_type
			me.parent_map = {};
			me.item_by_name = {};
			me.data = [];

			$.each(items, function(i, v) {
				var d = copy_dict(v);

				me.data.push(d);
				me.item_by_name[d.name] = d;
				if(d[me.tree_grid.parent_field]) {
					me.parent_map[d.name] = d[me.tree_grid.parent_field];
				}
				me.reset_item_values(d);
			});

			this.set_indent();

		} else {
			// otherwise, only reset values
			$.each(this.data, function(i, d) {
				me.reset_item_values(d);
			});
		}

		this.prepare_balances();
		if(me.tree_grid.show) {
			this.set_totals(false);
			this.update_groups();
		} else {
			this.set_totals(true);
		}

	},
	prepare_balances: function() {
		var me = this;
		var from_date = frappe.datetime.str_to_obj(this.from_date);
		var to_date = frappe.datetime.str_to_obj(this.to_date);
		var is_val = this.value_or_qty == 'Value';

		$.each(this.tl[this.based_on], function(i, tl) {
			if (me.is_default('company') ? true : tl.company === me.company) {
				var posting_date = frappe.datetime.str_to_obj(tl.posting_date);
				if (posting_date >= from_date && posting_date <= to_date) {
					var item = me.item_by_name[tl[me.tree_grid.item_key]] ||
						me.item_by_name['Not Set'];
					if(item){
						item[me.column_map[tl.posting_date].field] += (is_val ? tl.base_net_amount : tl.qty);
					}
				}
			}
		});
	},
	update_groups: function() {
		var me = this;

		$.each(this.data, function(i, item) {
			var parent = me.parent_map[item.name];
			while(parent) {
				var parent_group = me.item_by_name[parent];

				$.each(me.columns, function(c, col) {
					if (col.formatter == me.currency_formatter) {
						parent_group[col.field] =
							flt(parent_group[col.field])
							+ flt(item[col.field]);
					}
				});
				parent = me.parent_map[parent];
			}
		});
	},
	set_totals: function(sort) {
		var me = this;
		var checked = false;
		$.each(this.data, function(i, d) {
			d.total = 0.0;
			$.each(me.columns, function(i, col) {
				if(col.formatter==me.currency_formatter && !col.hidden && col.field!="total")
					d.total += d[col.field];
				if(d.checked) checked = true;
			})
		});

		if(sort)this.data = this.data.sort(function(a, b) { return a.total < b.total; });

		if(!this.checked) {
			this.data[0].checked = true;
		}
	}
});
