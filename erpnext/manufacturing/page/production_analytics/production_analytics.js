// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['production-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Production Analytics'),
		single_column: true
	});

	new erpnext.ProductionAnalytics(wrapper);
		

	frappe.breadcrumbs.add("Manufacturing");
}

erpnext.ProductionAnalytics = frappe.views.GridReportWithPlot.extend({
	init: function(wrapper) {
		this._super({
			title: __("Production Analytics"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Item", "Company", "Fiscal Year", "Production Order"]
		});

	},
	setup_columns: function() {

		var std_columns = [
			{id: "_check", name: __("Plot"), field: "_check", width: 30,
				formatter: this.check_formatter},
			{id: "name", name: __("Status"), field: "name", width: 100},
		];

		this.make_date_range_columns();
		this.columns = std_columns.concat(this.columns);
	},
	filters: [
				{fieldtype:"Select", label: __("Company"), link:"Company", fieldname: "company",
			default_value: __("Select Company...")},
		{fieldtype:"Date", label: __("From Date"), fieldname: "from_date"},
		{fieldtype:"Date", label: __("To Date"), fieldname: "to_date"},
		{fieldtype:"Select", label: __("Range"), fieldname: "range",
			options:[{label: __("Daily"), value: "Daily"}, {label: __("Weekly"), value: "Weekly"},
				{label: __("Monthly"), value: "Monthly"}, {label: __("Quarterly"), value: "Quarterly"},
				{label: __("Yearly"), value: "Yearly"}]}
	],
	setup_filters: function() {
		var me = this;
		this._super();

		this.trigger_refresh_on_change(["company"]);
		this.trigger_refresh_on_change(["range"]);

		this.show_zero_check()
		this.setup_chart_check();
	},
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Monthly');
	},

	prepare_data: function() {
		// add Opening, Closing, Totals rows
		// if filtered by account and / or voucher
		var me = this;
		var all_open_orders = {name:"All Production Orders", "id": "all-open-pos",
			checked:true};
		var not_started = {name:"Not Started", "id":"not-started-pos",
			checked:true};
		var overdue = {name:"Overdue (Not Started)", "id":"overdue-pos",
			checked:true};
		var  pending = {name:"Pending", "id":"pending-pos",
			checked:true};
		var completed = {name:"Completed", "id":"completed-pos",
			checked:true};
	

		$.each(frappe.report_dump.data["Production Order"], function(i, d) {
			var dateobj = dateutil.str_to_obj(d.creation);
			var date = d.creation.split(" ")[0];
			var col = me.column_map[date];

			if(col) {
				var start_period = dateutil.str_to_obj(col.name);
				var end_period = dateutil.str_to_obj(col.id);
				all_open_orders[col.field] = flt(all_open_orders[col.field]) + 1;
				if(d.status=="Completed") {
					completed[col.field] = flt(completed[col.field]) + 1;
				}else if(d.status=="In Process") {
					pending[col.field] = flt(pending[col.field]) + 1;
				}else if(d.status=="Not Started") {
					if (d.planned_start_date > start_period) {
						not_started[col.field] = flt(not_started[col.field]) + 1;
					}else if (d.planned_start_date < end_period) {
						overdue[col.field] = flt(overdue[col.field]) + 1;
					}else if (d.planned_start_date < d.actual_start_date) {
						not_started[col.field] = flt(not_started[col.field]) + 1;
					}else if (d.planned_start_date > dateutil.now_datetime()) {
						not_started[col.field] = flt(not_started[col.field]) + 1;
					}
					else{
						overdue[col.field] = flt(overdue[col.field]) + 1;
					}
				}
			}
		});

		this.data = [all_open_orders, not_started, overdue, pending, completed];
	}
});
