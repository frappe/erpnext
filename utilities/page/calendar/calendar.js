// Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
// 
// MIT License (MIT)
// 
// Permission is hereby granted, free of charge, to any person obtaining a 
// copy of this software and associated documentation files (the "Software"), 
// to deal in the Software without restriction, including without limitation 
// the rights to use, copy, modify, merge, publish, distribute, sublicense, 
// and/or sell copies of the Software, and to permit persons to whom the 
// Software is furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in 
// all copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
// INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
// PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
// HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
// CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
// OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
// 

pscript.onload_calendar = function(wrapper) {
	if(!erpnext.calendar) {
		erpnext.calendar = new Calendar();
		erpnext.calendar.init(wrapper);

		var me = this;
		$(document).bind('rename', function(event, dt, old_name, new_name) {
			erpnext.calendar.rename_notify(dt, old_name, new_name)
		});
	}
}

///// CALENDAR

Calendar=function() {
	this.views=[];
	this.events = {};
	this.events_by_name = {};
	this.weekdays = new Array("Sun","Mon","Tue","Wed","Thu","Fri","Sat");
}

Calendar.prototype.init=function (parent) {

	this.wrapper = parent;
 	this.body = $('.cal_body').get(0);

 	//this.make_head_buttons();
 	//this.make_header();
	this.view_title = $('.cal_view_title').get(0);
 	
	this.todays_date = new Date();
	this.selected_date = this.todays_date;
	this.selected_hour = 8;

	// Create views
	this.views['Month'] = new Calendar.MonthView(this);
	this.views['Week'] = new Calendar.WeekView(this);
	this.views['Day'] = new Calendar.DayView(this);

	// Month view as initial
	this.cur_view = this.views['Month'];
	this.views['Month'].show();
	
}

Calendar.prototype.rename_notify = function(dt, old_name, new_name) {
	// calendar
	if(dt = 'Event'){
		if(this.events_by_name[old_name]) {
			delete this.events_by_name[old_name];
		}
	}
}

//------------------------------------------------------

Calendar.prototype.show_event = function(ev, cal_ev) {
	var me = this;
	if(!this.event_dialog) {
		var d = new Dialog(400, 400, 'Calendar Event');
		d.make_body([
			['HTML','Heading']
			,['Text','Description']
			,['HTML', 'Ref Link']
			,['Check', 'Public Event']
			,['Check', 'Cancelled Event']
			,['HTML', 'Event Link']
			,['Button', 'Save']
		])
		
		// show the event when the dialog opens
		d.onshow = function() {
			// heading
			var c = me.selected_date;
			
			this.widgets['Heading'].innerHTML = 
				'<div style="text-align: center; padding:4px; font-size: 14px">'
				+ erpnext.calendar.weekdays[c.getDay()] + ', ' + c.getDate() + ' ' + month_list_full[c.getMonth()] + ' ' + c.getFullYear() 
				+ ' - <b>'+this.ev.event_hour+'</b></div>';
			
			// set
			this.widgets['Description'].value = cstr(this.ev.description);
			
			this.widgets['Public Event'].checked = false;
			this.widgets['Cancelled Event'].checked = false;

			if(this.ev.event_type=='Public')
				this.widgets['Public Event'].checked = true;
			
			this.widgets['Event Link'].innerHTML = '';
			this.widgets['Ref Link'].innerHTML = '';

			if(this.ev.ref_type) {
				$(repl('<table style="width: 100%;"><tr>\
					<td style="width: 30%"><b>Reference:</b></td>\
					<td><a href="#Form/%(ref_type)s/%(ref_name)s" \
					onclick="cur_dialog.hide()">%(ref_type)s: %(ref_name)s</a></td>\
				</tr></table>', this.ev))
						.appendTo(this.widgets['Ref Link'])
			}

			$(repl('<a href="#Form/Event/%(name)s" \
				onclick="cur_dialog.hide()">More Options</a>', this.ev))
					.appendTo(this.widgets['Event Link'])
		}
		
		// event save
		d.widgets['Save'].onclick = function() {
			var d = me.event_dialog;
			
			// save values
			d.ev.description = d.widgets['Description'].value;
			if(d.widgets['Cancelled Event'].checked) 
				d.ev.event_type='Cancel';
			else if(d.widgets['Public Event'].checked) 
				d.ev.event_type='Public';
			
			me.event_dialog.hide();
			
			// if new event
			me.save_event(d.ev);
		}
		this.event_dialog = d;
	}
	this.event_dialog.ev = ev;
	this.event_dialog.cal_ev = cal_ev ? cal_ev : null;
	this.event_dialog.show();
	
}

Calendar.prototype.save_event = function(doc) {
	var me = this;
	var doclist = new wn.model.DocList("Event", doc.name);
	doclist.save("Save", function(r) {
		var doc = locals['Event'][r.docname];
		var cal = erpnext.calendar;
		cal.cur_view.refresh();

		// if cancelled, hide
		if(doc.event_type=='Cancel') {
			$(cal.events_by_name[doc.name].body).toggle(false);
		}		
	})
}

//------------------------------------------------------

Calendar.prototype.add_event = function() {
		
	var ev = wn.model.make_new_doc_and_get_name('Event');
	ev = locals['Event'][ev];
	
	ev.event_date = dateutil.obj_to_str(this.selected_date);
	ev.event_hour = this.selected_hour+':00:00';
	ev.event_type = 'Private';

	this.show_event(ev);
}
//------------------------------------------------------

Calendar.prototype.get_month_events = function(call_back) {
	// ret fn
	var me = this;
	var f = function(r, rt) {
		if(me.cur_view) me.cur_view.refresh();
		if(call_back)call_back();
	}

	//load
	var y=this.selected_date.getFullYear(); var m = this.selected_date.getMonth();
	if(!this.events[y] || !this.events[y][m]) {
		$c('webnotes.widgets.event.load_month_events', args = {
			'month': m + 1, 
			'year' : y},
			f);	
	}
}
//------------------------------------------------------

Calendar.prototype.get_daily_event_list=function(day) {
	var el = [];
	var d = day.getDate(); var m = day.getMonth(); var y = day.getFullYear()
	if(this.events[y] && this.events[y][m] &&
		this.events[y][m][d]) {
		var l = this.events[y][m][d]
		for(var i in l) {
			for(var j in l[i]) el[el.length] = l[i][j];
		}
		return el;
	}
	else return [];
}
//------------------------------------------------------

Calendar.prototype.set_event = function(ev) {
	// don't duplicate
	if(this.events_by_name[ev.name]) {
		return this.events_by_name[ev.name];
	}
		
	var dt = dateutil.str_to_obj(ev.event_date);
	var m = dt.getMonth();
	var d = dt.getDate();
	var y = dt.getFullYear();

	if(!this.events[y]) this.events[y] = [];
	if(!this.events[y][m]) this.events[y][m] = [];
	if(!this.events[y][m][d]) this.events[y][m][d] = [];
	if(!this.events[y][m][d][cint(ev.event_hour)]) 
		this.events[y][m][d][cint(ev.event_hour)] = [];

	var cal_ev = new Calendar.CalEvent(ev, this);
	this.events[y][m][d][cint(ev.event_hour)].push(cal_ev);	
	this.events_by_name[ev.name] = cal_ev;
	
	return cal_ev;
}

//------------------------------------------------------

Calendar.prototype.clear = function() {
	this.events = {};
	this.events_by_name = {};
	locals.Event = {};
}

Calendar.prototype.refresh = function(viewtype, clear_events){//Sets the viewtype of the Calendar and Calls the View class based on the viewtype
 	if(viewtype)
 		this.viewtype = viewtype;

	if(clear_events)
		this.clear();
		
 	// switch view if reqd
 	if(this.cur_view.viewtype!=this.viewtype) {
 		this.cur_view.hide();
 		this.cur_view = this.views[this.viewtype];
 		this.cur_view.in_home = false; // for home page
 		this.cur_view.show();
 	}
 	else{
 		this.cur_view.get_events();
 		this.cur_view.refresh(this);
 	}
}

//------------------------------------------------------

Calendar.CalEvent= function(doc, cal) {
	var me = this;
	me.doc = doc;
	
	this.body = $("<div class='label cal_event'></div>")
		.html(doc.description)
		.attr("title", doc.description)
		.css({"cursor":"pointer"})
		.attr("data-event", doc.name)
		.click(function() {
			var doc = locals["Event"][$(this).attr("data-event")];
			cal.show_event(doc, me);
		})

	this.show = function(vu) {
		me.body
			.html(me.doc.description)
			.css({"width": ($(vu.body).width()-10)})
			.appendTo(vu.body)
			.removeClass("label-success").removeClass("label-info")
			.addClass(me.doc.event_type=="Public" ? "label-success" : "label-info")
	}
}


// ----------

Calendar.View =function() { this.daystep = 0; this.monthstep = 0; }
Calendar.View.prototype.init=function(cal) {
 	this.cal = cal;
 	this.body = $a(cal.body, 'div', 'cal_view_body');
 	this.body.style.display = 'none';
 	this.create_table();
}


Calendar.View.prototype.show=function() { 
	this.body.style.display = 'block';
	this.get_events(); this.refresh();  
}

Calendar.View.prototype.hide=function() { 
	this.body.style.display = 'none';
}

Calendar.View.prototype.next = function() {
	var s = this.cal.selected_date;
	this.cal.selected_date = new Date(s.getFullYear(), s.getMonth() + this.monthstep, s.getDate() + this.daystep);
	this.get_events(); this.refresh();
}

Calendar.View.prototype.prev = function() {
	var s = this.cal.selected_date;
	this.cal.selected_date = new Date(s.getFullYear(), s.getMonth() - this.monthstep, s.getDate() - this.daystep);
	this.get_events(); this.refresh();
}

Calendar.View.prototype.get_events = function() { 
	this.cal.get_month_events(); 
}
Calendar.View.prototype.add_unit = function(vu) { 
	this.viewunits[this.viewunits.length] = vu; 
}
Calendar.View.prototype.refresh_units = function() { 
	// load the events
	if(locals['Event']) {
		for(var name in locals['Event']) {
			this.cal.set_event(locals['Event'][name]);
		}
	}
	
	
	for(var r in this.table.rows) {
		for(var c in this.table.rows[r].cells) {
			if(this.table.rows[r].cells[c].viewunit) {
				this.table.rows[r].cells[c].viewunit.refresh();
			}
		}
	}
}

// ................. Month View..........................
Calendar.MonthView = function(cal) { this.init(cal); this.monthstep = 1; this.rows = 5; this.cells = 7; }
Calendar.MonthView.prototype=new Calendar.View();
Calendar.MonthView.prototype.create_table = function() {

	// create head
	this.head_wrapper = $a(this.body, 'div', 'cal_month_head');

	// create headers
	this.headtable = $a(this.head_wrapper, 'table', 'cal_month_headtable');
	var r = this.headtable.insertRow(0);
	for(var j=0;j<7;j++) {
 		var cell = r.insertCell(j);
		cell.innerHTML = erpnext.calendar.weekdays[j]; 
		$w(cell, (100 / 7) + '%');
 	}

	this.main = $a(this.body, 'div', 'cal_month_body');
	this.table = $a(this.main, 'table', 'cal_month_table');
	var me = this;

	// create body
 	for(var i=0;i<5;i++) {
 		var r = this.table.insertRow(i);
 		for(var j=0;j<7;j++) {
 			var cell = r.insertCell(j);
			cell.viewunit = new Calendar.MonthViewUnit(cell);
 		}
  	}  	
}

Calendar.MonthView.prototype.refresh = function() {
 	var c =this.cal.selected_date;
	var	me=this;
	// fill other days

	var cur_row = 0; 

 	var cur_month = c.getMonth();
 	var cur_year = c.getFullYear();

 	var d = new Date(cur_year, cur_month, 1);
	var day = 1 - d.getDay();
	

	// set day headers
 	var d = new Date(cur_year, cur_month, day);

	this.cal.view_title.innerHTML = month_list_full[cur_month] + ' ' + cur_year;

 	for(var i=0;i<6;i++) {
 		if((i<5) || cur_month==d.getMonth()) { // if this month
	 		for(var j=0;j<7;j++) {
				var cell = this.table.rows[cur_row].cells[j];

		 		if((i<5) || cur_month==d.getMonth()) {	// if this month
					cell.viewunit.day = d;
					cell.viewunit.hour = 8;
			 		if(cur_month == d.getMonth()) {
						cell.viewunit.is_disabled = false;
	
						if(same_day(this.cal.todays_date, d))
							cell.viewunit.is_today = true;
						else
							cell.viewunit.is_today = false;					
						
					} else {
						cell.viewunit.is_disabled = true;
					}
				}
				// new date
	 			day++;
		 		d = new Date(cur_year, cur_month, day);
	 		}
	 	}
		cur_row++;
 		if(cur_row == 5) {cur_row = 0;} // back to top
	}
	this.refresh_units();
	
}
 // ................. Daily View..........................
Calendar.DayView=function(cal){ this.init(cal); this.daystep = 1; }
Calendar.DayView.prototype=new Calendar.View();
Calendar.DayView.prototype.create_table = function() {

	// create body
	this.main = $a(this.body, 'div', 'cal_day_body');
	this.table = $a(this.main, 'table', 'cal_day_table');
	var me = this;
	
 	for(var i=0;i<24;i++) {
 		var r = this.table.insertRow(i);
 		for(var j=0;j<2;j++) {
 			var cell = r.insertCell(j);
			if(j==0) {
				cell.innerHTML = i+':00:00';
				$w(cell, '10%');
			} else {
				cell.viewunit = new Calendar.DayViewUnit(cell);
				cell.viewunit.hour = i;
				$w(cell, '90%');
				if((i>=7)&&(i<=20)) {
					cell.viewunit.is_daytime = true;
				}
			}
 		}
  	}
 }

Calendar.DayView.prototype.refresh = function() {
	var c =this.cal.selected_date;
			
	// fill other days
	var me=this;

	this.cal.view_title.innerHTML = erpnext.calendar.weekdays[c.getDay()] + ', ' 
		+ c.getDate() + ' ' + month_list_full[c.getMonth()] + ' ' + c.getFullYear();

	// headers
	var d = c;

	for(var i=0;i<24;i++) {
		var cell = this.table.rows[i].cells[1];
		if(same_day(this.cal.todays_date, d)) cell.viewunit.is_today = true;
		else cell.viewunit.is_today = false;
		cell.viewunit.day = d;
	}
	 this.refresh_units();
}

// ................. Weekly View..........................
Calendar.WeekView=function(cal) { this.init(cal); this.daystep = 7; }
Calendar.WeekView.prototype=new Calendar.View();
Calendar.WeekView.prototype.create_table = function() {

	// create head
	this.head_wrapper = $a(this.body, 'div', 'cal_month_head');

	// day headers
	this.headtable = $a(this.head_wrapper, 'table', 'cal_month_headtable');
	var r = this.headtable.insertRow(0);
	for(var j=0;j<8;j++) {
 		var cell = r.insertCell(j);
 	}
 	
 	// hour header

	// create body
	this.main = $a(this.body, 'div', 'cal_week_body');
	this.table = $a(this.main, 'table', 'cal_week_table');
	var me = this;
	
 	for(var i=0;i<24;i++) {
 		var r = this.table.insertRow(i);
 		for(var j=0;j<8;j++) {
 			var cell = r.insertCell(j);
			if(j==0) {
				cell.innerHTML = i+':00:00';
				$w(cell, '10%');
			} else {
				cell.viewunit = new Calendar.WeekViewUnit(cell);
				cell.viewunit.hour = i;
				if((i>=7)&&(i<=20)) {
					cell.viewunit.is_daytime = true;
				}
			}
 		}
  	}
}

Calendar.WeekView.prototype.refresh = function() {
	var c =this.cal.selected_date;
	// fill other days
	var me=this;

	this.cal.view_title.innerHTML = month_list_full[c.getMonth()] + ' ' + c.getFullYear();

	// headers
	var d = new Date(c.getFullYear(), c.getMonth(), c.getDate() - c.getDay());

	for (var k=1;k<8;k++) 	{
		this.headtable.rows[0].cells[k].innerHTML = erpnext.calendar.weekdays[d.getDay()] + ' ' + d.getDate();

		for(var i=0;i<24;i++) {
			var cell = this.table.rows[i].cells[k];
			if(same_day(this.cal.todays_date, d)) 
				cell.viewunit.is_today = true;
			else cell.viewunit.is_today = false;

			cell.viewunit.day = d;
			//cell.viewunit.refresh();
		}
		d=new Date(d.getFullYear(),d.getMonth(),d.getDate() + 1);

	 }
	 
	 this.refresh_units();
}

//------------------------------------------------------.

Calendar.ViewUnit = function() {}
Calendar.ViewUnit.prototype.init = function(parent) {
	parent.style.border = "1px solid #CCC"	;
	this.body = $a(parent, 'div', this.default_class);
	this.parent = parent;

	var me = this;
	this.body.onclick = function() {
		erpnext.calendar.selected_date = me.day;
		erpnext.calendar.selected_hour = me.hour;
	
		if(erpnext.calendar.cur_vu && erpnext.calendar.cur_vu!=me){
			erpnext.calendar.cur_vu.deselect();
			me.select();
			erpnext.calendar.cur_vu = me;
		}
	}
	this.body.ondblclick = function() {
		erpnext.calendar.add_event();
	}
}

Calendar.ViewUnit.prototype.set_header=function(v) {
 	this.header.innerHTML = v;
}

Calendar.ViewUnit.prototype.set_today = function() {
	this.is_today = true;
	this.set_display();
}

Calendar.ViewUnit.prototype.clear = function() {
	if(this.header)this.header.innerHTML = '';

	// clear body
	while(this.body.childNodes.length)
		this.body.removeChild(this.body.childNodes[0]);
}

Calendar.ViewUnit.prototype.set_display = function() {
	var cn = '#FFF';

	// colors
	var col_tod_sel = '#EEE';
	var col_tod = '#FFF';
	var col_sel = '#EEF';

	if(this.is_today) {
		if(this.selected) cn = col_tod_sel;
		else cn = col_tod;
	} else 
		if(this.selected) cn = col_sel;
	
	if(this.header) {
		if(this.is_disabled) {
			this.body.className = this.default_class + ' cal_vu_disabled';
			this.header.style.color = '#BBB';
		} else {
			this.body.className = this.default_class;
			this.header.style.color = '#000';		
		}
		
		if(this.day&&this.day.getDay()==0)
			this.header.style.backgroundColor = '#FEE';
		else 
			this.header.style.backgroundColor = '';
	}
	this.parent.style.backgroundColor = cn;
}

Calendar.ViewUnit.prototype.is_selected = function() {
	return (same_day(this.day, erpnext.calendar.selected_date)
		&& this.hour==erpnext.calendar.selected_hour)
}

Calendar.ViewUnit.prototype.get_event_list = function() {
	var y = this.day.getFullYear();
	var m = this.day.getMonth();
	var d = this.day.getDate();
	if(erpnext.calendar.events[y] && erpnext.calendar.events[y][m] &&
		erpnext.calendar.events[y][m][d] &&
			erpnext.calendar.events[y][m][d][this.hour]) {
		return erpnext.calendar.events[y][m][d][this.hour];
	} else
		return [];
}

Calendar.ViewUnit.prototype.refresh = function() {
	this.clear();

	if(this.is_selected()) { 
		if(erpnext.calendar.cur_vu)erpnext.calendar.cur_vu.deselect();
		this.selected = true;
		erpnext.calendar.cur_vu = this;	
	}
	this.set_display();
	this.el = this.get_event_list();
	if(this.onrefresh)this.onrefresh();	

	for(var i in this.el) {
		this.el[i].show(this);
	}
		
	var me = this;
}

Calendar.ViewUnit.prototype.select=function() { this.selected = true; this.set_display(); }
Calendar.ViewUnit.prototype.deselect=function() { this.selected = false; this.set_display(); }
Calendar.ViewUnit.prototype.setevent=function() { }

Calendar.MonthViewUnit=function(parent) {
	var me = this;
	this.header = $("<div class='cal_month_date'></div>")
		.appendTo(parent)
		.css({"cursor":"pointer"})
		.click(function() {
			me.body.onclick();
		})
		.bind("dblclick", function() {
			me.body.ondblclick();
		})
		.get(0);

	this.default_class = "cal_month_unit";	
	this.init(parent);

	this.onrefresh = function() {
		this.header.innerHTML = this.day.getDate();
	}
}
Calendar.MonthViewUnit.prototype = new Calendar.ViewUnit();
Calendar.MonthViewUnit.prototype.is_selected = function() {
	return same_day(this.day, erpnext.calendar.selected_date)
}

Calendar.MonthViewUnit.prototype.get_event_list = function() {
	return erpnext.calendar.get_daily_event_list(this.day);
}

Calendar.DayViewUnit= function(parent) { 
	this.default_class = "cal_day_unit"; this.init(parent); 
}
Calendar.DayViewUnit.prototype = new Calendar.ViewUnit();
Calendar.DayViewUnit.prototype.onrefresh = function() {
	if(this.el.length<3) 
		this.body.style.height = '30px';
	else this.body.style.height = '';
}

Calendar.WeekViewUnit=function(parent) { 
	this.default_class = "cal_week_unit"; this.init(parent); 
}
Calendar.WeekViewUnit.prototype = new Calendar.ViewUnit();
Calendar.WeekViewUnit.prototype.onrefresh = function() {
	if(this.el.length<3) this.body.style.height = '30px';
	else this.body.style.height = '';
}
