// render
wn.doclistviews['Maintenance Visit'] = wn.views.ListView.extend({
	me: this,

	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabMaintenance Visit`.customer_name",
			"`tabMaintenance Visit`.mntc_date",
			"`tabMaintenance Visit`.mntc_time",
			"`tabMaintenance Visit`.maintenance_type",
			"`tabMaintenance Visit`.completion_status",
			
		]);
		this.stats = this.stats.concat(['completion_status', 'company']);
		//this.show_hide_check_column();
	},
	
	prepare_data: function(data) {
		this._super(data);
		data.mntc_date = wn.datetime.str_to_user(data.mntc_date);
		data.mntc_time = wn.datetime.time_to_ampm(data.mntc_time);
		data.date_time = "on " + data.mntc_date + " at " + 
			data.mntc_time[0] + ":" + data.mntc_time[1] + " " + data.mntc_time[2];
		data.customer_name = data.customer_name + " " + data.date_time;
		data.completion_status = data.completion_status + 
			(data.maintenance_type ? " [" + data.maintenance_type + "]": "");
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '15%', content: 'name'},
		{width: '40%', content: 'customer_name+tags'},
		{width: '20%', content: 'completion_status'},
		{width: '14%', content: 'modified',
			css: {'text-align': 'right', 'color':'#777'}}
	]

});
