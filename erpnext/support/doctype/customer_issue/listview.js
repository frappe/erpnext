// render
wn.doclistviews['Customer Issue'] = wn.views.ListView.extend({
	me: this,

	init: function(d) {
		this._super(d)
		this.fields = this.fields.concat([
			"`tabCustomer Issue`.customer",
			"`tabCustomer Issue`.serial_no",
			"`tabCustomer Issue`.item_name",
			"`tabCustomer Issue`.complaint",
			"`tabCustomer Issue`.status",
		]);
		this.stats = this.stats.concat(['status', 'company']);
		//this.show_hide_check_column();
	},
	
	prepare_data: function(data) {
		this._super(data);
		if(data.status=='Open') {
			data.label_type = 'important';
		} else if(data.status=='Closed') {
			data.label_type = 'success';
		} else if(data.status=='Cancelled') {
			data.label_type = 'info';
		} else if(data.status=='Work In Progress') {
			data.label_type = 'info';
			data.status = 'WIP';
		}
		
		data.status_html = repl(
			'<span class="label label-%(label_type)s">%(status)s</span>', data);
		var a = $(data.status_html).click(function() {
			me.set_filter('status', $(this).text());
		});
		
		var concat_list = [data.customer];
		data.serial_no && concat_list.push(data.serial_no);
		data.complaint && concat_list.push(data.complaint);
		data.complaint = concat_list.join(" | ");
		
		// description
		if(data.complaint && data.complaint.length > 50) {
			data.complaint = '<span title="'+data.complaint+'">' + 
				data.complaint.substr(0,50) + '...</span>';
		}
	},
	
	columns: [
		{width: '3%', content: 'check'},
		{width: '5%', content: 'avatar'},
		{width: '3%', content: 'docstatus'},
		{width: '20%', content: 'name'},
		{width: '10%', content: 'status_html'},
		{width: '47%', content: 'complaint+tags', css: {color:'#777'}},
		{width: '12%', content: 'modified',
			css: {'text-align': 'right', 'color':'#777'}}
	]

});
