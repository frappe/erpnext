// render
wn.doclistviews['Sales Order'] = {
	fields: [
		{ field: "name", name: "ID"},
		{ field: "owner", name: "Created By"},
		{ field: "modified", name: "Last Updated"},
		{ field: "customer_name", name: "Customer", width:300},
		{ field: "per_delivered", name: "% Delivered", 
			query: "ifnull(per_delivered,0) as per_delivered"}, 
		{ field: "per_billed", name: "% Billed", 
			query: "ifnull(per_billed,0) as per_billed"}, 
		{ field: "currency", name: "Currency"},
		{ field: "grand_total_export", name: "Grand Total", 
			query:"ifnull(grand_total_export,0) as grand_total_export"},
		{ field: "docstatus", name: "Status"}
	],
	render: function(row, data, listobj) {
		data.modified_date = dateutil.str_to_user(data.modified).split(' ')[0];
		
		// bar color for billed
		data.bar_class_delivered = ''; data.bar_class_billed = '';
		if(data.per_delivered == 100) data.bar_class_delivered = 'bar-complete';
		if(data.per_billed == 100) data.bar_class_billed = 'bar-complete';
		
		// lock for docstatus
		data.icon = '';
		if(data.docstatus==1) {
			data.icon = ' <i class="icon-lock" title="Submitted"></i>';
		}
		
		$(row).html(repl('<span class="avatar-small"><img src="%(avatar)s" /></span>\
			<a href="#!Form/%(doctype)s/%(name)s">%(name)s</a>\
			%(icon)s\
			<span style="color:#444">%(customer_name)s</span>\
			<span class="bar-outer" style="width: 30px; float: right" \
				title="%(per_delivered)s% Delivered">\
				<span class="bar-inner %(bar_class_delivered)s" \
					style="width: %(per_delivered)s%;"></span>\
			</span>\
			<span class="bar-outer" style="width: 30px; float: right" \
				title="%(per_billed)s% Billed">\
				<span class="bar-inner %(bar_class_billed)s" \
					style="width: %(per_billed)s%;"></span>\
			</span>\
			<span style="float:right; font-size: 11px; color: #888;\
				margin-left: 7px;">%(modified_date)s</span>\
			<span style="color:#444; float: right;">%(currency)s %(grand_total_export)s</span>\
			', data)).addClass('list-row');
	}
}
