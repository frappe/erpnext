wn.pages['activity'].onload = function(wrapper) {
	var list = new wn.widgets.Listing({
		method: 'home.page.activity.activity.get_feed',
		parent: $('#activity-list'),
		render_row: function(row, data) {
			new erpnext.ActivityFeed(row, data);
		}
	});
	list.run();
}

erpnext.last_feed_date = false;
erpnext.ActivityFeed = Class.extend({
	init: function(row, data) {
		this.scrub_data(data);
		this.add_date_separator(row, data);
		$(row).append(repl('<span %(onclick)s\
			class="label %(add_class)s">%(feed_type)s</span>\
			%(link)s %(subject)s <span class="user-info">%(by)s</span>', data));
	},
	scrub_data: function(data) {
		data.by = wn.boot.user_fullnames[data.owner];
		
		// feedtype
		if(!data.feed_type) {
			data.feed_type = get_doctype_label(data.doc_type);
			data.add_class = "label-info";
			data.onclick = repl('onclick="window.location.href=\'#!List/%(feed_type)s\';"', data)
		}
		
		// color for comment
		if(data.feed_type=='Comment') {
			data.add_class = "label-important";
		}
		
		if(data.feed_type=='Assignment') {
			data.add_class = "label-warning";
		}
		
		// link
		if(data.doc_name && data.feed_type!='Login') {
			data.link = repl('<a href="#!Form/%(doc_type)s/%(doc_name)s">%(doc_name)s</a>', data)
		}
	},
	add_date_separator: function(row, data) {
		var date = dateutil.str_to_obj(data.modified);
		var last = erpnext.last_feed_date;
		
		if((last && dateutil.get_diff(last, date)>1) || (!last)) {
			var pdate = dateutil.comment_when(date);
			var diff = dateutil.get_diff(new Date(), date);
			if(diff < 1) {
				pdate = 'Today';
			} else if(diff > 6) {
				pdate = dateutil.global_date_format(date);
			}
			$(row).html(repl('<div class="date-sep">%(date)s</div>', {date: pdate}));
		}
		erpnext.last_feed_date = date;
	}
})