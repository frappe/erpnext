pscript['onload_Event Updates'] = function() {
	if(user=='Guest') {
		loadpage('Login Page');
		return;
	}
			
	pscript.home_make_body();
	pscript.home_make_status();
	pscript.home_pre_process();
	pscript.home_make_widgets();
}

// ==================================

pscript.home_make_body = function() {
	var wrapper = page_body.pages['Event Updates'];
	
	// body
	wrapper.main_tab = make_table(wrapper,1,2,'100%',['70%','30%']);
	$y(wrapper.main_tab, {tableLayout:'fixed'});

	wrapper.body = $a($td(wrapper.main_tab, 0, 0), 'div', 'layout_wrapper');

	wrapper.head = $a(wrapper.body, 'div');
	
	wrapper.banner_area = $a(wrapper.head, 'div');
	wrapper.toolbar_area = $a(wrapper.head, 'div');


	wrapper.system_message_area = $a(wrapper.body, 'div', '', 
		{marginBottom:'16px', padding:'8px', backgroundColor:'#FFD', border:'1px dashed #AA6', display:'none'})
	
	
}

// ==================================

pscript.home_pre_process = function(wrapper) {
	var wrapper = page_body.pages['Event Updates'];
	var cp = locals['Control Panel']['Control Panel'];

	// banner
	if(cp.client_name) {
		var banner = $a(wrapper.banner_area, 'div', '', {paddingBottom:'4px'})
		banner.innerHTML = cp.client_name;
	}

	// complete registration
	if(in_list(user_roles,'System Manager')) { pscript.complete_registration(); }	
}

// Widgets
// ==================================

pscript.home_make_widgets = function() {
	var wrapper = page_body.pages['Event Updates'];
	var cell = $td(wrapper.main_tab, 0, 1);

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
	})
	sidebar.refresh()

	/*$y(cell,{padding:'0px 8px'});

	new HomeCalendar(new HomeWidget(cell, 'Calendar', 'Event'));
	
	
	new HomeToDo(new HomeWidget(cell, 'To Do', 'Item'));*/
	
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
	this.add_btn = $btn(this.footer,'+ Add ' + item,function(){me.add()});

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
	$c_obj('Home Control',this.widget.delete_method, this.widget.get_item_id(this.det) ,callback);
		
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
	this.widget.get_item_id = function(det) { return det[0]; }

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
		,backgroundColor:(det[3]=='Low' ? '#888' : (det[3]=='High' ? '#EDA857' : '#687FD3'))});
		
	$(span).css('-moz-border-radius','3px').css('-webkit-border-radius','3px');
	span.innerHTML = det[3];

	// text
	var span = $a($td(tab, 0, 1), 'span', 'social', {lineHeight:'1.5em'}, replace_newlines(det[1]));
	if(det[4]) $y(span,{textDecoration:'line-through'});
	
	// if expired & open, then in red
	if(!det[4] && dateutil.str_to_obj(det[2]) < new Date()) {
		$y(span,{color:'RED'}); 
		$a($td(tab, 0, 1), 'div', '', {fontSize:'10px', color:'#666'}, dateutil.str_to_user(det[2]) + ' (Overdue)');
	} else {
		$a($td(tab, 0, 1), 'div', '', {fontSize:'10px', color:'#666'}, dateutil.str_to_user(det[2]));		
	}
}

HomeToDo.prototype.clear_dialog = function() {
	this.set_dialog_values(['','',get_today(),'Medium',0]);
}

HomeToDo.prototype.set_dialog_values = function(det) {
	var d = this.widget.dialog;
	d.set_values({
		date: det[2],
		priority: det[3],
		description: det[1],
		checked: det[4]
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

	det.name = d.det ? d.det[0] : '';
	
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
	$a(this.head,'span','link_type', {marginLeft:'7px'}, '[?]', function() {
		msgprint('<b>What appears here?</b> This is where you get updates of everything you are allowed to access and generates an update')
	})

	// refresh
	$a(this.head,'span','link_type', 
		{cursor:'pointer', marginLeft:'7px', fontSize:'11px'}, 'refresh',
		function() { me.run(); }
	);
}

FeedList.prototype.run = function() {
	this.prev_date = null;
	this.list.run();
}

FeedList.prototype.make_list = function() {
	this.list_area = $a(this.wrapper,'div')
	this.no_result = $a(this.wrapper, 'div','help_box',{display:'none'},'Nothing to show yet. Your feed will be updated as you start your activities')
	
	var l = new Listing('Feed List',1);
	var me = this;

	// style
	l.colwidths = ['100%']; l.page_len = 20;	
	l.opts.cell_style = {padding:'0px'};
	l.opts.hide_rec_label = 1;
	
	// build query
	l.get_query = function(){
		this.query = repl('select \
			distinct t1.name, t1.doc_type, t1.doc_name, t1.subject, t1.modified_by, \
			concat(ifnull(t2.first_name,""), " ", ifnull(t2.last_name,"")), t1.modified, t1.color \
			from tabFeed t1, tabProfile t2, tabUserRole t3, tabDocPerm t4 \
			where t1.doc_type = t4.parent \
			and t2.name = t1.owner \
			and t3.parent = "%(user)s" \
			and t4.role = t3.role \
			and ifnull(t4.`read`,0) = 1 \
			order by t1.modified desc', {user:user})
		this.query_max = ''
	}
	
	// render list ui
	l.show_cell = function(cell,ri,ci,d){ me.render_feed(cell,ri,ci,d); }
	
	// onrun
	l.onrun = function(){ $(me.wrapper).fadeIn(); if(me.after_run) me.after_run(); }
	
	// make
	l.make(this.list_area);
	$dh(l.btn_area);

	this.list = l;
}

FeedList.prototype.after_run = function() {
	this.list.has_data() ? $dh(this.no_result) : $ds(this.no_result)
}

FeedList.prototype.render_feed = function(cell,ri,ci,d) {
	new FeedItem(cell, d[ri], this);
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

	// image
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
	var prev_date = det[6].split(' ')[0];
	
	var make_div = function() {
		var div = $a(me.head, 'div', '', 
			{borderBottom:'1px solid #888', margin:'8px 0px', padding:'2px 0px', color:'#888', fontSize:'11px'});
		div.innerHTML = comment_when(det[6], 1);
		
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
	tag = $a($td(this.tab,0,0), 'div', '', 
		{color:'#FFF', padding:'3px', textAlign:'right', fontSize:'11px', whiteSpace:'nowrap', overflow:'hidden', cursor:'pointer'});
	$br(tag,'3px');
	$y(tag, {backgroundColor:(det[7] ? det[7] : '#273')});
	tag.innerHTML = get_doctype_label(det[1]);
	tag.dt = det[1]
	tag.onclick = function() { loaddocbrowser(this.dt); }
}

FeedItem.prototype.render_references = function(div, det) {
	// name
	div.tab = make_table(div, 1, 2, '100%', [null, '15%'])
	//div.innerHTML = '<b>' + (strip(det[11]) ? det[11] : det[2]) + ' (' + cint(det[12]) + '): </b> has ' + det[7] + ' ';
	
	var dt = det[1]; var dn = det[2]
	
	// link
	var allow = in_list(profile.can_read, dt);
	var span = $a($td(div.tab,0,0), 'span', (allow ? 'link_type': ''), null, det[2]);
	span.dt = dt; span.dn = dn;
	if(allow) span.onclick = function() { loaddoc(this.dt, this.dn); }
	
	// subject
	if(det[3]) {
		$a($td(div.tab,0,0), 'span', '', {marginLeft:'7px', color:'#444'}, det[3]);
	}
	
	// by
	$y($td(div.tab,0,1), {fontSize:'11px'}).innerHTML = (strip(det[5]) ? det[5] : det[4]);
}

HomeStatusBar = function() {
	var me = this;
	var parent = page_body.pages['Event Updates'];
	this.wrapper = $a($td(parent.main_tab, 0, 1), 'div', 'home-status', {}, 'Loading...');
	$br(this.wrapper, '3px');
	
	this.render = function(r) {
		this.wrapper.innerHTML = '';
		this.span = $a(this.wrapper, 'span', 'home-status-link')
		this.span.onclick = function() { loadpage('My Company')	}
		
		if(r.unread_messages) {
			this.span.innerHTML = '<span class="home-status-unread">' + r.unread_messages + '</span> unread message' + (cint(r.unread_messages) > 1 ? 's' : '');
		} else {
			this.span.innerHTML = 'No unread messages.';
		}
	}
}

pscript.home_make_status = function() {
	var home_status_bar = new HomeStatusBar()
	var wrapper = page_body.pages['Event Updates'];

	// get values
	$c_page('event_updates', 'event_updates', 'get_status_details', user,
		function(r,rt) { 
			
			home_status_bar.render(r.message);
			
			// system_messages
			if(r.message.system_message)
				pscript.show_system_message(wrapper, r.message.system_message);
				
			// trial
			if(pscript.is_erpnext_saas && cint(r.message.is_trial) && in_list(user_roles, 'System Manager')) {
				pscript.trial_box = $a(div, 'div', 'help_box', {margin:'2px 8px 2px 0px'}, "Your Free Trial expires in " +
				r.message.days_to_expiry + " days. When you are satisfied, please <span class='link_type' onclick='pscript.convert_to_paid()'>please click here</span> to convert to a paid account." + 
				"<br>To get help, view <a href='http://erpnext.blogspot.com/2011/02/getting-started-with-your-erpnext.html' target='_blank'>Getting Started with Your System</a> (opens in a new page)");
			}
			
			// render online users
			pscript.online_users_obj.render(r.message.online_users);
			pscript.online_users = r.message.online_users;
		}
	);	
}

// show system message
// -------------------
pscript.convert_to_paid = function() {
	var callback = function(r,rt) {
		if(r.exc) { msgprint(r.exc); return; }
		$(pscript.trial_box).slideUp();
	}
	$c_page('event_updates','event_updates','convert_to_paid','',callback)	
}

// show system message
// -------------------
pscript.show_system_message = function(wrapper, msg) {
	$ds(wrapper.system_message_area);
	var txt = $a(wrapper.system_message_area, 'div', '', {lineHeight:'1.6em'});
	txt.innerHTML = msg;
	
	var span = $ln($a(wrapper.system_message_area, 'div'), 'Dismiss', 
		function(me) { 
			me.set_working();
			$c_obj('Home Control', 'dismiss_message', '', function(r,rt) { 
				me.done_working(); 
				$(wrapper.system_message_area).slideUp(); 
			});
		}, {fontSize:'11px'}
	)
}

// complete my company registration
// --------------------------------
pscript.complete_registration = function()
{
	var reg_callback = function(r, rt){
		if(r.message == 'No'){
			var d = new Dialog(400, 200, "Please Complete Your Registration");
			if(user != 'Administrator'){
				d.no_cancel(); // Hide close image
				$dh(page_body.wntoolbar.wrapper);
			}
			$($a(d.body,'div','', {margin:'8px', color:'#888'})).html('<b>Company Name : </b>'+locals['Control Panel']['Control Panel'].company_name);      

			d.make_body(
		  [
		  	['Data','Company Abbreviation'],
		  	['Select','Fiscal Year Start Date'],
		  	['Select','Default Currency'],
		  	['Button','Save'],
			]);

			//d.widgets['Save'].disabled = true;      // disable Save button
			pscript.make_dialog_field(d);

			// submit details
			d.widgets['Save'].onclick = function()
			{
				d.widgets['Save'].set_working();
				
				flag = pscript.validate_fields(d);
				if(flag)
				{
					var args = [
						locals['Control Panel']['Control Panel'].company_name,
						d.widgets['Company Abbreviation'].value,
						d.widgets['Fiscal Year Start Date'].value,
						d.widgets['Default Currency'].value
					];
					
					$c_obj('Setup Control','setup_account',JSON.stringify(args),function(r, rt){
						sys_defaults = r.message;
						d.hide();
						$ds(page_body.wntoolbar.wrapper);
					});
				}
			}
			d.show();
		}
	}
	$c_obj('Home Control','registration_complete','',reg_callback);
}

// make dialog fields
// ------------------
pscript.make_dialog_field = function(d)
{
	// fiscal year format 
	fisc_format = d.widgets['Fiscal Year Start Date'];
	add_sel_options(fisc_format, ['', '1st Jan', '1st Apr', '1st Jul', '1st Oct']);
  
	// default currency
	currency_list = ['', 'AED', 'AFN', 'ALL', 'AMD', 'ANG', 'AOA', 'ARS', 'AUD', 'AZN', 'BAM', 'BBD', 'BDT', 'BGN', 'BHD', 'BIF', 'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BTN', 'BYR', 'BZD', 'CAD', 'CDF', 'CFA', 'CFP', 'CHF', 'CLP', 'CNY', 'COP', 'CRC', 'CUC', 'CZK', 'DJF', 'DKK', 'DOP', 'DZD', 'EEK', 'EGP', 'ERN', 'ETB', 'EUR', 'EURO', 'FJD', 'FKP', 'FMG', 'GBP', 'GEL', 'GHS', 'GIP', 'GMD', 'GNF', 'GQE', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 'HTG', 'HUF', 'IDR', 'ILS', 'INR', 'IQD', 'IRR', 'ISK', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 'KHR', 'KMF', 'KPW', 'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 'LTL', 'LVL', 'LYD', 'MAD', 'MDL', 'MGA', 'MKD', 'MMK', 'MNT', 'MOP', 'MRO', 'MUR', 'MVR', 'MWK', 'MXN', 'MYR', 'MZM', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NRs', 'NZD', 'OMR', 'PAB', 'PEN', 'PGK', 'PHP', 'PKR', 'PLN', 'PYG', 'QAR', 'RMB', 'RON', 'RSD', 'RUB', 'RWF', 'SAR', 'SCR', 'SDG', 'SDR', 'SEK', 'SGD', 'SHP', 'SOS', 'SRD', 'STD', 'SYP', 'SZL', 'THB', 'TJS', 'TMT', 'TND', 'TRY', 'TTD', 'TWD', 'TZS', 'UAE', 'UAH', 'UGX', 'USD', 'USh', 'UYU', 'UZS', 'VEB', 'VND', 'VUV', 'WST', 'XAF', 'XCD', 'XDR', 'XOF', 'XPF', 'YEN', 'YER', 'YTL', 'ZAR', 'ZMK', 'ZWR'];
	currency = d.widgets['Default Currency'];
	add_sel_options(currency, currency_list);
}


// validate fields
// ---------------
pscript.validate_fields = function(d)
{
	var lst = ['Company Abbreviation', 'Fiscal Year Start Date', 'Default Currency'];
	var msg = 'Please enter the following fields';
	var flag = 1;
	for(var i=0; i<lst.length; i++)
	{
		if(!d.widgets[lst[i]].value){
			flag = 0;
			msg = msg + NEWLINE + lst[i];
		}
	}

	if(!flag)  alert(msg);
	return flag;
}
