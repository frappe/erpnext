// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.pages['activity'].onload = function(wrapper) {
	wn.ui.make_app_page({
		parent: wrapper,
		title: wn._("Activity"),
		single_column: true
	})
	wrapper.appframe.add_module_icon("Activity");
	
	var list = new wn.ui.Listing({
		hide_refresh: true,
		appframe: wrapper.appframe,
		method: 'home.page.activity.activity.get_feed',
		parent: $(wrapper).find(".layout-main"),
		render_row: function(row, data) {
			new erpnext.ActivityFeed(row, data);
		}
	});
	list.run();

	wrapper.appframe.set_title_right("Refresh", function() { list.run(); });
	
	// Build Report Button
	if(wn.boot.profile.can_get_report.indexOf("Feed")!=-1) {
		wrapper.appframe.add_primary_action(wn._('Build Report'), function() {
			wn.set_route('Report', "Feed");
		}, 'icon-th')
	}
}

erpnext.last_feed_date = false;
erpnext.ActivityFeed = Class.extend({
	init: function(row, data) {
		this.scrub_data(data);
		this.add_date_separator(row, data);
		if(!data.add_class) data.add_class = "label-default";
		$(row).append(repl('<div style="margin: 0px">\
			<span class="avatar avatar-small"><img src="%(imgsrc)s" /></span> \
			<span %(onclick)s class="label %(add_class)s">%(feed_type)s</span>\
			%(link)s %(subject)s <span class="user-info">%(by)s</span></div>', data));
	},
	scrub_data: function(data) {
		data.by = wn.user_info(data.owner).fullname;
		data.imgsrc = wn.utils.get_file_link(wn.user_info(data.owner).image);
		
		// feedtype
		if(!data.feed_type) {
			data.feed_type = wn._(data.doc_type);
			data.add_class = "label-info";
			data.onclick = repl('onclick="window.location.href=\'#!List/%(feed_type)s\';"', data)
		}
		
		// color for comment
		if(data.feed_type=='Comment') {
			data.add_class = "label-danger";
		}
		
		if(data.feed_type=='Assignment') {
			data.add_class = "label-warning";
		}
		
		// link
		if(data.doc_name && data.feed_type!='Login') {
			data.link = wn.format(data.doc_name, {"fieldtype":"Link", "options":data.doc_type})
		} else {
			data.link = "";
		}
	},
	add_date_separator: function(row, data) {
		var date = dateutil.str_to_obj(data.modified);
		var last = erpnext.last_feed_date;
		
		if((last && dateutil.obj_to_str(last) != dateutil.obj_to_str(date)) || (!last)) {
			var diff = dateutil.get_day_diff(new Date(), date);
			if(diff < 1) {
				pdate = 'Today';
			} else if(diff < 2) {
				pdate = 'Yesterday';
			} else {
				pdate = dateutil.global_date_format(date);
			}
			$(row).html(repl('<div class="date-sep">%(date)s</div>', {date: pdate}));
		}
		erpnext.last_feed_date = date;
	}
})