// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.pages['support-analytics'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Support Analytics'),
		single_column: true
	});

	new erpnext.SupportAnalytics(wrapper);


	frappe.breadcrumbs.add("Support")

}

erpnext.SupportAnalytics = frappe.views.GridReportWithPlot.extend({
	init: function(wrapper) {
		this._super({
			title: __("Support Analtyics"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			page: wrapper.page,
			doctypes: ["Issue", "Fiscal Year"],
		});
	},

	filters: [
		{fieldname: "fiscal_year", fieldtype:"Select", label: __("Fiscal Year"), link:"Fiscal Year",
			default_value: __("Select Fiscal Year") + "..."},
		{fieldname: "from_date", fieldtype:"Date", label: __("From Date")},
		{fieldname: "to_date", fieldtype:"Date", label: __("To Date")},
		{fieldname: "range", fieldtype:"Select", label: __("Range"),
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"], default_value: "Monthly"}
	],
	
	init_filter_values: function() {
		this._super();
		this.filter_inputs.range.val('Monthly');
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

	prepare_data: function() {
		// add Opening, Closing, Totals rows
		// if filtered by account and / or voucher
		var me = this;
		var total_tickets = {name:"All Tickets", "id": "all-tickets",
			checked:true};
		var days_to_close = {name:"Days to Close", "id":"days-to-close",
			checked:false};
		var total_closed = {};
		var hours_to_close = {name:"Hours to Close", "id":"hours-to-close",
			checked:false};
		var hours_to_respond = {name:"Hours to Respond", "id":"hours-to-respond",
			checked:false};
		var total_responded = {};


		$.each(frappe.report_dump.data["Issue"], function(i, d) {
			var dateobj = dateutil.str_to_obj(d.creation);
			var date = d.creation.split(" ")[0];
			var col = me.column_map[date];
			if(col) {
				total_tickets[col.field] = flt(total_tickets[col.field]) + 1;
				if(d.status=="Closed") {
					// just count
					total_closed[col.field] = flt(total_closed[col.field]) + 1;

					days_to_close[col.field] = flt(days_to_close[col.field])
						+ dateutil.get_diff(d.resolution_date, d.creation);

					hours_to_close[col.field] = flt(hours_to_close[col.field])
						+ dateutil.get_hour_diff(d.resolution_date, d.creation);

				}
				if (d.first_responded_on) {
					total_responded[col.field] = flt(total_responded[col.field]) + 1;

					hours_to_respond[col.field] = flt(hours_to_respond[col.field])
						+ dateutil.get_hour_diff(d.first_responded_on, d.creation);
				}
			}
		});

		// make averages
		$.each(this.columns, function(i, col) {
			if(col.formatter==me.currency_formatter && total_tickets[col.field]) {
				days_to_close[col.field] = flt(days_to_close[col.field]) /
					flt(total_closed[col.field]);
				hours_to_close[col.field] = flt(hours_to_close[col.field]) /
					flt(total_closed[col.field]);
				hours_to_respond[col.field] = flt(hours_to_respond[col.field]) /
					flt(total_responded[col.field]);
			}
		})

		this.data = [total_tickets, days_to_close, hours_to_close, hours_to_respond];
	}
});
