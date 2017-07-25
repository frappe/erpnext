frappe.pages['appointment-analytic'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Appointment Analytics',
		single_column: true
	});
	new erpnext.AppointmentAnalytics(wrapper);
	frappe.breadcrumbs.add("Medical");
};

erpnext.AppointmentAnalytics = frappe.views.TreeGridReport.extend({
	init: function(wrapper) {
		this._super({
			title: __("Appointment Analytics"),
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Patient Appointment", "Physician", "Medical Department", "Appointment Type", "Patient"],
			tree_grid: { show: true }
		});

		this.tree_grids = {
			"Medical Department": {
				label: __("Department"),
				show: true,
				item_key: "physician",
				parent_field: "department",
				formatter: function(item) {
					return item.name;
				}
			},
			"Physician": {
				label: __("Physician"),
				show: true,
				item_key: "physician",
				formatter: function(item) {
					return item.name;
				}
			},
		};
	},
	setup_columns: function() {
		this.tree_grid = this.tree_grids[this.tree_type];

		var std_columns = [
			{id: "_check", name: __("Plot"), field: "_check", width: 40,
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
		{fieldtype:"Select", label: __("Tree Type"), fieldname: "tree_type",
			options:["Physician", "Medical Department"], filter: function(val, item, opts, me) {
				return me.apply_zero_filter(val, item, opts, me);}},
		{fieldtype:"Select", label: __("Status"), fieldname: "status",
			options:[
				{label: __("Select Status"), value: "Select Status..."},
				{label: __("Open"), value: "Open"},
				{label: __("Closed"), value: "Closed"},
				{label: __("Pending"), value: "Pending"},
				{label: __("Scheduled"), value: "Scheduled"},
				{label: __("Cancelled"), value: "Cancelled"}]},
		{fieldtype:"Select", label: __("Type"), link:"Appointment Type", fieldname: "type",
			default_value: __("Select Type...")},
		{fieldtype:"Select", label: __("Physician"), link:"Physician", fieldname: "physician",
			default_value: __("Select Physician..."), filter: function(val, item, opts) {
				return val == opts.default_value || item.name == val || item._show;
			}, link_formatter: {filter_input: "physician"}},
		{fieldtype:"Select", label: __("Department"), link:"Medical Department", fieldname: "department",
			default_value: __("Select Department..."), filter: function(val, item, opts) {
				return val == opts.default_value || item.department == val || item._show;
			}, link_formatter: {filter_input: "department"}},
		{fieldtype:"Date", label: __("From Date"), fieldname: "from_date"},
		{fieldtype:"Date", label: __("To Date"), fieldname: "to_date"},
		{fieldtype:"Select", label: __("Range"), fieldname: "range",
			options:[{label: __("Daily"), value: "Daily"}, {label: __("Weekly"), value: "Weekly"},
				{label: __("Monthly"), value: "Monthly"}, {label: __("Quarterly"), value: "Quarterly"},
				{label: __("Yearly"), value: "Yearly"}]}
	],
	setup_filters: function() {
		this._super();
		this.trigger_refresh_on_change(["tree_type", "physician", "department", "status", "type"]);

		//	this.show_zero_check()
		this.setup_chart_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Quarterly');
	},
	prepare_data: function() {
		var me = this;
		if (!this.tl) {
			this.tl = frappe.report_dump.data["Patient Appointment"];
		}
		if(!this.data || me.item_type != me.tree_type) {
			var items = null;
			if(me.tree_type=='Physician') {
				items = frappe.report_dump.data["Physician"];
			} if(me.tree_type=='Medical Department') {
				items = this.prepare_tree("Physician", "Medical Department");
			}
			me.item_type = me.tree_type;
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
		var status = this.status;
		var type = this.type;
		var to_date = frappe.datetime.str_to_obj(this.to_date);
		$.each(this.tl, function(i, tl) {
			if (me.is_default('company') ? true : tl.company === me.company) {

				var date = frappe.datetime.str_to_obj(tl.appointment_date);
				if (date >= from_date && date <= to_date) {
					var item = me.item_by_name[tl[me.tree_grid.item_key]] ||
						me.item_by_name['Not Set'];

					var d = tl.appointment_date.split(" ")[0];
					if(status == "Select Status..." && type=="Select Type...")
					{
						item[me.column_map[d].field] += 1;

					}else if (status !== "Select Status..." && type == "Select Type..."){
						if(status === tl.status){item[me.column_map[d].field] += 1;}
					}else if (status == "Select Status..." && type !== "Select Type..."){
						if(type === tl.appointment_type){item[me.column_map[d].field] += 1;}
					}else {
						if(type === tl.appointment_type && status === tl.status){item[me.column_map[d].field] += 1;}
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
		$.each(this.data, function(i, d) {
			d.total = 0.0;
			$.each(me.columns, function(i, col) {
				if(col.formatter==me.currency_formatter && !col.hidden && col.field!="total")
					d.total += d[col.field];
			});
		});

		if(sort)this.data = this.data.sort(function(a, b) { return b.total - a.total; });

		if(!this.checked) {
			this.data[0].checked = true;
		}
	}

});
