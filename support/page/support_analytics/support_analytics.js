// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['support-analytics'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._('Support Analytics'),
		single_column: true
	});					

	new erpnext.SupportAnalytics(wrapper);
	

	wrapper.appframe.add_module_icon("Support")
	
}

erpnext.SupportAnalytics = wn.views.GridReportWithPlot.extend({
	init: function(wrapper) {
		this._super({
			title: wn._("Support Analtyics"),
			page: wrapper,
			parent: $(wrapper).find('.layout-main'),
			appframe: wrapper.appframe,
			doctypes: ["Support Ticket", "Fiscal Year"],
		});
	},
	
	filters: [
		{fieldtype:"Select", label: wn._("Fiscal Year"), link:"Fiscal Year", 
			default_value: "Select Fiscal Year..."},
		{fieldtype:"Date", label: wn._("From Date")},
		{fieldtype:"Label", label: wn._("To")},
		{fieldtype:"Date", label: wn._("To Date")},
		{fieldtype:"Select", label: wn._("Range"), 
			options:["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]},
		{fieldtype:"Button", label: wn._("Refresh"), icon:"icon-refresh icon-white"},
		{fieldtype:"Button", label: wn._("Reset Filters")}
	],

	setup_columns: function() {
		var std_columns = [
			{id: "check", name: wn._("Plot"), field: "check", width: 30,
				formatter: this.check_formatter},
			{id: "status", name: wn._("Status"), field: "status", width: 100},
		];
		this.make_date_range_columns();		
		this.columns = std_columns.concat(this.columns);
	},
	
	prepare_data: function() {
		// add Opening, Closing, Totals rows
		// if filtered by account and / or voucher
		var me = this;
		var total_tickets = {status:"All Tickets", "id": "all-tickets",
			checked:true};
		var days_to_close = {status:"Days to Close", "id":"days-to-close",
			checked:false};
		var total_closed = {};
		var hours_to_close = {status:"Hours to Close", "id":"hours-to-close", 
			checked:false};
		var hours_to_respond = {status:"Hours to Respond", "id":"hours-to-respond", 
			checked:false};
		var total_responded = {};

		
		$.each(wn.report_dump.data["Support Ticket"], function(i, d) {
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
	},

	get_plot_points: function(item, col, idx) {
		return [[dateutil.str_to_obj(col.id).getTime(), item[col.field]], 
			[dateutil.user_to_obj(col.name).getTime(), item[col.field]]];
	}
	
});