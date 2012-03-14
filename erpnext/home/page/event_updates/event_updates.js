// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

pscript['onload_Event Updates'] = function() {
	if(user=='Guest') {
		loadpage('Login Page');
		return;
	}
			
	pscript.home_make_body();
	pscript.home_make_status();
	pscript.home_set_banner();
	pscript.home_make_widgets();
}

// ==================================

pscript.home_make_body = function() {
	var wrapper = wn.pages['Event Updates'];
	
	// body
	$(wrapper).addClass('layout-wrapper').addClass('layout-wrapper-background')
	
	wrapper.body = $a(wrapper, 'div', 'layout-main-section');
	wrapper.head = $a(wrapper.body, 'div');
	wrapper.side_section =$a(wrapper, 'div', 'layout-side-section');
	$a(wrapper, 'div', '', {clear:'both'});
	
	wrapper.banner_area = $a(wrapper.head, 'div');

	wrapper.setup_wizard_area = $a(wrapper.body, 'div', 'setup-wizard');	
}

// ==================================

pscript.home_set_banner = function(wrapper) {
	var wrapper = wn.pages['Event Updates'];
	var cp = wn.control_panel;

	// banner
	if(cp.client_name) {
		var banner = $a(wrapper.banner_area, 'div', '', {paddingBottom:'4px'})
		banner.innerHTML = cp.client_name;
	}
}

// Widgets
// ==================================

pscript.home_make_widgets = function() {
	var wrapper = wn.pages['Event Updates'];
	var cell = wrapper.side_section;

	// sidebar
	sidebar = new wn.widgets.PageSidebar(cell, {
		sections:[
			{
				title: 'Calendar',
				display: function() { return !has_common(user_roles, ['Guest','Customer','Vendor'])},
				render: function(wrapper) {
					new HomeCalendar(new HomeWidget(wrapper, 'Calendar', 'Event'), wrapper);
				}		
			},
			
			{
				title: 'To Do',
				display: function() { return !has_common(user_roles, ['Guest','Customer','Vendor'])},
				render: function(wrapper) {
					new HomeToDo(new HomeWidget(wrapper, 'To Do', 'Item'));
				}		
			},

			{
				title: 'Online Users',
				display: function() { return !has_common(user_roles, ['Guest','Customer','Vendor'])},
				render: function(wrapper) {
					pscript.online_users_obj = new OnlineUsers(wrapper);
				}		
			}
		]
	});
		
	new FeedList(wrapper.body);
}

OnlineUsers = function(wrapper) {
	var me = this;
	this.wrapper = wrapper;
	
	this.my_company_link = function() {
		$a($a(wrapper, 'div', '', {marginBottom:'7px'}), 'span', 'link_type', 
			{color:'#777', 'color:hover':'#FFF', fontSize:'11px'}, 
			'See all users', function() {loadpage('My Company'); });
	}
	
	this.render = function(online_users) {
		me.my_company_link();
		
		if(online_users.length) {
			var max = online_users.length; max = (max > 10 ? 10 : max)
			me.wrapper.innerHTML = "";
			for(var i=0; i<max; i++) {
				new OneOnlineUser(me.wrapper, online_users[i]);
			}
		} else {
			$a(wrapper, 'div', '', {'color':'#888'}, 'No user online!')
		}
	}
}

OneOnlineUser = function(wrapper, det) {
	var name = cstr(det[1]) + ' ' + cstr(det[2]);
	if(det[1]==user) name = 'You'
	var div = $a(wrapper, 'div', '', {padding:'3px 0px'});
	$a(div, 'div', '', {width:'7px', height:'7px', cssFloat:'left', margin:'5px', backgroundColor:'green'});
	$a(div, 'div', '', {marginLeft:'3px'}, name);
}

HomeWidget = function(parent, heading, item) {
	var me = this; this.item = item;
	
	this.wrapper = $a(parent, 'div');
	
	
	// body
	this.body = $a(this.wrapper,'div','',{paddingBottom:'16px'});
	this.footer = $a(this.wrapper,'div');
	
	// add button
	this.add_btn = $btn(this.footer,'+ Add ' + item,function(){me.add()},null,'cupid-blue');

	// refresh
	this.refresh_btn = $ln(this.footer,'Refresh',function() { me.refresh(); },{fontSize:'11px',marginLeft:'7px',color:'#888'});
}

HomeWidget.prototype.refresh = function() {
	var me = this;
	$di(this.working_img);
		
	var callback = function(r,rt) {
		$dh(me.working_img);
		me.body.innerHTML = '';

		// prepare (for calendar?)
		if(me.decorator.setup_body) me.decorator.setup_body();

		for(var i=0;i<r.message.length;i++) {
			new HomeWidgetItem(me, r.message[i]);
		}
		if(!r.message.length) {
			$a(me.body,'div','',{color:'#777'}, me.no_items_message);
		}
	}
	$c_obj('Home Control',this.get_list_method,'',callback);
}

HomeWidget.prototype.make_dialog = function() {
	var me = this;
	if(!this.dialog) {
		this.dialog = new wn.widgets.Dialog();
		this.dialog.make({
			width: 480,
			title: 'New ' + this.item, 
			fields:this.dialog_fields
		});
		
		this.dialog.fields_dict.save.input.onclick = function() {
			this.set_working();
			me.decorator.save(this);	
		}
	}
}

HomeWidget.prototype.add = function() {
	this.make_dialog();
	this.decorator.clear_dialog();
	this.dialog.show();
}

// Item
// --------

HomeWidgetItem = function(widget, det) {
	var me = this; this.det = det; this.widget = widget;
	this.widget = widget; this.det = det;
	
	// parent
	if(widget.decorator.get_item_parent) parent = widget.decorator.get_item_parent(det);
	else parent = widget.body;
	
	if(!parent) return;
	
	// wrapper
	this.wrapper = $a(parent, 'div');
	this.tab = make_table(this.wrapper, 1, 3, '100%', ['90%', '5%', '5%'],{paddingRight:'4px'});

	// buttons
	this.edit_btn = $a($td(this.tab,0,1),'div','wn-icon ' + 'ic-doc_edit', {cursor:'pointer'});
	this.edit_btn.onclick = function() { me.edit(); }

	this.del_btn = $a($td(this.tab,0,2),'div','wn-icon ' + 'ic-trash', {cursor:'pointer'});
	this.del_btn.onclick = function() { me.delete_item(); }

	widget.decorator.render_item(this, det);
}

HomeWidgetItem.prototype.edit = function() {
	this.widget.make_dialog();
	this.widget.decorator.set_dialog_values(this.det);
	this.widget.dialog.show();
}

HomeWidgetItem.prototype.delete_item = function() {
	var me = this;
	this.wrapper.innerHTML = '<span style="color:#888">Deleting...</span>';
	var callback = function(r,rt) {
		$(me.wrapper).slideUp();
	}
	$c_obj('Home Control',this.widget.delete_method, 
		this.widget.get_item_id(this.det) ,callback);
		
}

// Calendar
// ===========================

HomeCalendar = function(widget, wrapper) {
	// calendar link
	$ln(widget.footer,'Full Calendar',function() { loadpage('_calendar'); },{marginLeft:'7px', fontSize:'11px', color:'#888'})

	this.widget = widget;

	// methods
	this.widget.get_list_method = 'get_events_list'
	this.widget.delete_method = 'delete_event';
	this.widget.no_items_message = 'You have no events in the next 7 days';
	this.widget.get_item_id = function(det) { return det.name; }

	this.widget.decorator = this;

	var hl = [];
	for(var i=0; i<24; i++) {
		hl.push(((i+8) % 24) + ':00');
	}

	this.widget.dialog_fields = [
		{fieldtype:'Date', fieldname:'event_date', label:'Event Date', reqd:1},
		{fieldtype:'Time', fieldname:'event_hour', label:'Event Time', reqd:1},
		{fieldtype:'Text', fieldname:'description', label:'Description', reqd:1},
		{fieldtype:'Button', fieldname:'save', label:'Save'}
	];

	this.widget.refresh();
}

// create calendar grid
// --------------------
HomeCalendar.prototype.setup_body = function() {
	var w = this.widget;
	w.date_blocks = {};
	for(var i=0; i<7; i++) {
		var dt = dateutil.obj_to_str(dateutil.add_days(new Date(),i));
		var div = $a(w.body, 'div', '', {padding:'4px 0px', borderBottom:'1px solid #AAA',display:'none'});
		div.head = $a(div, 'div', '', {fontWeight:'bold', paddingBottom:'4px'});
		div.head.innerHTML  = (i==0 ? 'Today' : (i==1 ? 'Tomorrow' : dateutil.str_to_user(dt)))
		w.date_blocks[dt] = div;
	}
}

HomeCalendar.prototype.get_item_parent = function(det) {
	var d = this.widget.date_blocks[det.event_date]; $ds(d);
	return d;
}

HomeCalendar.prototype.render_item = function(item, det) {	
	var tab = make_table($td(item.tab, 0, 0), 1, 2, '100%', ['48px', null], {padding:'2px', lineHeight:'1.5em'});
	$y(tab, {tableLayout:'fixed'});

	$td(tab, 0, 0).innerHTML = '<span style="color:#888">' + det.event_hour + ':</span> ';
	$a($td(tab, 0, 1), 'span', 'social', {}, replace_newlines(det.description));

	if(det.ref_type && det.ref_name && det.ref_name != 'None') {
		var span=$a($a($td(tab, 0, 1),'div'),'span','link_type');
		span.innerHTML = det.ref_name; span.dt = det.ref_type;
		span.onclick = function() { loaddoc(this.dt, this.innerHTML); }
	}
}

HomeCalendar.prototype.clear_dialog = function() {
	this.set_dialog_values({event_date:get_today(), event_hour:'8:00', description:''});
}

HomeCalendar.prototype.set_dialog_values = function(det) {
	var d = this.widget.dialog;
	d.set_values(det);
	d.det = det;
}

HomeCalendar.prototype.save = function(btn) {
	var d = this.widget.dialog;
	var me = this;
	var det = d.get_values();
	
	if(!det) {
		btn.done_working();
	 	return;
	}
	
	det.name = d.det.name;
	det.owner = user;
	if(!det.event_type)
		det.event_type = 'Private';
	
	var callback = function(r,rt) {
		btn.done_working();
		me.widget.dialog.hide();
		me.widget.refresh();
	}
	$c_obj('Home Control','edit_event',JSON.stringify(det),callback);	
}

// Todo
// ===========================

HomeToDo = function(widget) {
	this.widget = widget;

	// methods
	this.widget.get_list_method = 'get_todo_list';
	this.widget.delete_method = 'remove_todo_item';
	this.widget.no_items_message = 'Nothing to do?';
	this.widget.get_item_id = function(det) { return det.name; }

	this.widget.decorator = this;

	this.widget.dialog_fields = [
		{fieldtype:'Date', fieldname:'date', label:'Event Date', reqd:1},
		{fieldtype:'Text', fieldname:'description', label:'Description', reqd:1},
		{fieldtype:'Check', fieldname:'checked', label:'Completed'},
		{fieldtype:'Select', fieldname:'priority', label:'Priority', reqd:1, 'options':['Medium','High','Low'].join('\n')},
		{fieldtype:'Button', fieldname:'save', label:'Save'}
	];

	this.widget.refresh();	
}

HomeToDo.prototype.render_item = function(item, det) {
	
	// priority tag
	var tab = make_table($td(item.tab, 0, 0), 1, 2, '100%', ['48px', null], {padding:'2px'});
	$y(tab, {tableLayout:'fixed'});

	var span = $a($td(tab, 0, 0), 'span', '', {padding:'2px',color:'#FFF',fontSize:'10px'
		, backgroundColor:(det.priority=='Low' ? '#888' : 
			(det.priority=='High' ? '#EDA857' : '#687FD3'))});
		
	$(span).css('-moz-border-radius','3px').css('-webkit-border-radius','3px');
	span.innerHTML = det.priority;

	// text
	var span = $a($td(tab, 0, 1), 'div', 'social', {lineHeight:'1.5em'}, 
		replace_newlines(det.description));
	if(det.checked) $y(span,{textDecoration:'line-through'});
	
	// reference link
	if(det.reference_name) {
		$a($td(tab, 0, 1), 'div', 'social', '', 
			repl('<a href="#!Form/%(reference_type)s/%(reference_name)s">%(reference_name)s</a>',
				det))
	}
	
	// if expired & open, then in red
	if(!det.checked && dateutil.str_to_obj(det.date) < new Date()) {
		$y(span,{color:'RED'}); 
		$a($td(tab, 0, 1), 'div', '', {fontSize:'10px', color:'#666'},
		 	dateutil.str_to_user(det.date) + ' (Overdue)');
	} else {
		$a($td(tab, 0, 1), 'div', '', {fontSize:'10px', color:'#666'}, 
			dateutil.str_to_user(det.date));		
	}
}

HomeToDo.prototype.clear_dialog = function() {
	this.set_dialog_values(['','',get_today(),'Medium',0]);
}

HomeToDo.prototype.set_dialog_values = function(det) {
	var d = this.widget.dialog;
	d.set_values({
		date: det.date,
		priority: det.priority,
		description: det.description,
		checked: det.checked
	});
	d.det = det;
}

HomeToDo.prototype.save = function(btn) {
	var d = this.widget.dialog;
	var me = this;
	
	var det = d.get_values()
	if(!det) {
		btn.done_working();
	 	return;	
	}

	det.name = d.det.name;
	var callback = function(r,rt) {
		btn.done_working();
		me.widget.dialog.hide();
		me.widget.refresh();
	}
	$c_obj('Home Control','add_todo_item',JSON.stringify(det),callback);	
}

// Feed
// ==================================


FeedList = function(parent) {
	// settings
	this.auto_feed_off = cint(sys_defaults.auto_feed_off);
	
	this.wrapper = $a(parent, 'div');
	this.make_head();
	this.make_list();
	this.list.run();
}

FeedList.prototype.make_head = function() {
	var me = this;
	this.head = $a(this.wrapper, 'div', '', {marginBottom:'8px'});
	
	// head

	$a(this.head,'h1','', {display:'inline'}, 'Home'); 

	// refresh
	$a(this.head,'span','link_type', 
		{marginLeft:'7px', fontSize:'11px'}, 'refresh',
		function() { me.run(); }
	);
	
	if(has_common(user_roles, ['System Manager','Accounts Manager'])) {
		$btn(this.head, 'Dashboard', function() {loadpage('dashboard'); }, {marginLeft:'7px'}, 'cupid-blue')
		
	}
}

FeedList.prototype.run = function() {
	this.prev_date = null;
	this.list.run();
}

FeedList.prototype.make_list = function() {
	var me = this;
	this.list_area = $a(this.wrapper,'div')
	
	this.list = new wn.ui.Listing({
		parent: this.list_area,
		query: repl('select \
			distinct t1.name, t1.feed_type, t1.doc_type, t1.doc_name, t1.subject, t1.modified_by, \
			if(ifnull(t1.full_name,"")="", t1.owner, t1.full_name) as full_name, \
			t1.modified, t1.color \
			from tabFeed t1, tabUserRole t3, tabDocPerm t4 \
			where t1.doc_type = t4.parent \
			and t3.parent = "%(user)s" \
			and t4.role = t3.role \
			and ifnull(t4.`read`,0) = 1 \
			order by t1.modified desc', {user:user}),
		no_result_message: 'Nothing to show yet. Your feed will be updated as you start your activities',
		render_row: function(parent, data) {
			me.render_feed(parent, data)
		},
		onrun: function() {
			$(me.wrapper).fadeIn(); 
			if(me.after_run) me.after_run();
		},
		hide_refresh: true
	});
}

FeedList.prototype.render_feed = function(parent, data) {
	new FeedItem(parent, data, this);
}

// Item
// -------------------------------

FeedItem = function(cell, det, feedlist) {
	var me = this;
	
	this.det = det; this.feedlist = feedlist;
	this.wrapper = $a(cell,'div','',{paddingBottom:'4px'});
	this.head = $a(this.wrapper,'div');

	this.tab = make_table(this.wrapper, 1, 2, '100%', [(100/7)+'%', (600/7)+'%']);
	$y(this.tab,{tableLayout:'fixed'})

	$y($td(this.tab,0,0),{textAlign:'right',paddingRight:'4px'});
	
	// text
	this.text_area = $a($td(this.tab,0,1), 'div');
	this.render_references(this.text_area, det);	
	this.render_tag(det);
	
	// add day separator
	this.add_day_sep(det);
}

// Day separator
// -------------------------------------------------

FeedItem.prototype.add_day_sep = function(det) {
	var me = this;
	var prev_date = det.modified.split(' ')[0];
	
	var make_div = function() {
		var div = $a(me.head, 'div', '', 
			{borderBottom:'1px solid #888', margin:'8px 0px', padding:'2px 0px', color:'#888', fontSize:'11px'});
		div.innerHTML = comment_when(det.modified, 1);
		
		// today?
		if(prev_date==get_today()) {
			div.innerHTML = '';
			span = $a(div, 'span', '', {padding:'2px', color:'#000', fontWeight:'bold'});
			span.innerHTML = 'Today';
		}
	}
	
	if(this.feedlist.prev_date && this.feedlist.prev_date != prev_date) { make_div(); }
	if(!this.feedlist.prev_date) { make_div(); }
	this.feedlist.prev_date = prev_date;
}

// Tag
// -------------------------------------------------

FeedItem.prototype.render_tag = function(det) {
	// type is the name
	tag = $a($td(this.tab,0,0), 'div', '', 
		{color:'#FFF', padding:'3px', textAlign:'right', fontSize:'11px', 
			whiteSpace:'nowrap', overflow:'hidden', cursor:'pointer'});
	$br(tag,'3px');
	$y(tag, {backgroundColor:(det.color || '#273')});
	
	// tag label
	tag.innerHTML = det.feed_type || get_doctype_label(det.doc_type);
	
	// not comment / label
	if(!det.feed_type) {
		tag.dt = det.doc_type;
		tag.onclick = function() { loaddocbrowser(this.dt); }		
	}
}

FeedItem.prototype.render_references = function(div, det) {
	// name
	div.tab = make_table(div, 1, 2, '100%', [null, '15%'])	
	var dt = det.doc_type; var dn = det.doc_name
	
	// link
	if(det.feed_type=='Login') {
		// nothing - no link		
	} else {
		var allow = in_list(profile.can_read, dt);
		var span = $a($td(div.tab,0,0), 'span', (allow ? 'link_type': ''), null, 
			det.doc_name);
		span.dt = dt; span.dn = dn;
		if(allow) span.onclick = function() { loaddoc(this.dt, this.dn); }		
	}
	
	// subject
	if(det.subject) {
		$a($td(div.tab,0,0), 'span', '', {marginLeft:'7px', color:'#444'}, det.subject);
	}
	
	// by
	$y($td(div.tab,0,1), {fontSize:'11px'}).innerHTML = 
		(strip(det.full_name) ? det.full_name : det.modified_by);
}

pscript.home_make_status = function() {
	var wrapper = wn.pages['Event Updates'];

	// get values
	$c_page('home', 'event_updates', 'get_status_details', user,
		function(r,rt) { 
			//page_body.wntoolbar.set_new_comments(r.message.unread_messages);
										
			// render online users
			pscript.online_users_obj.render(r.message.online_users);
			pscript.online_users = r.message.online_users;
	
			// complete registration
			if(in_list(user_roles,'System Manager')) { 
				wn.require("erpnext/home/page/event_updates/complete_registration.js");
				pscript.complete_registration(r.message.registration_complete, r.message.profile); 
			}
			
			// setup wizard
			if(r.message.setup_status) {
				new SetupWizard(r.message.setup_status)
			}
		}
	);	
}

SetupWizard = function(status) { 
	var me = this;
	$.extend(this, {
		make: function(status) {
			me.status = status;
			me.wrapper = wn.pages['Event Updates'].setup_wizard_area;
			$ds(me.wrapper);
			me.make_percent(status.percent);
			me.make_suggestion(status.ret);
		},
		make_percent: function(percent) {
			$a(me.wrapper, 'div', 'header', {}, 'Your setup is '+percent+'% complete');
			var o = $a(me.wrapper, 'div', 'percent-outer');
			$a(o, 'div', 'percent-inner', {width:percent + '%'});
		},
		make_suggestion: function(ret) {
			me.suggest_area = $a(me.wrapper, 'div', 'suggestion');
			if(me.status.ret.length>1) {
				me.prev_next = $a(me.wrapper, 'div', 'prev-next');

				// next
				me.next = $a(me.prev_next, 'span', 'link_type', null, 'Next Suggestion',
					function() { me.show_suggestion(me.cur_sugg+1) });

				// prev
				me.prev = $a(me.prev_next, 'span', 'link_type', null, 'Previous Suggestion',
					function() { me.show_suggestion(me.cur_sugg-1) });

			}
			if(me.status.ret.length) {
				me.show_suggestion(0);
			} else {
				me.suggest_area.innerHTML = 'Congratulations: '.bold() + 'You are now on your track... Good luck';
			}
		},
		show_suggestion: function(idx) {
			me.cur_sugg = idx;
			me.suggest_area.innerHTML = 'What you can do next: '.bold() + me.status.ret[idx];

			// show hide prev, next
			if(me.status.ret.length>1) {
				$dh(me.prev); $dh(me.next);
				if(idx>0) $ds(me.prev);
				if(idx<me.status.ret.length-1) $ds(me.next);			
			}
		}
	})
	this.make(status); 
}
