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

wn.provide("erpnext.calendar");

pscript.onload_calendar = function(wrapper) {
	wn.ui.make_app_page({
		parent: wrapper,
		single_column: true,
		title: 'Calendar'
	});
	
	wn.require('lib/js/lib/fullcalendar/fullcalendar.css');
	wn.require('lib/js/lib/fullcalendar/fullcalendar.js');
}

pscript.onshow_calendar = function(wrapper) {
	if(!wrapper.setup_complete) {
		erpnext.calendar.setup(wrapper);
	} else {
		$("#fullcalendar").fullCalendar("refetchEvents");
	}
}

erpnext.calendar.setup = function(wrapper) {
	wn.model.with_doctype("Event", function() {
		$('<div id="fullcalendar">').appendTo($(wrapper).find('.layout-main')).fullCalendar({
			header: {
				left: 'prev,next today',
				center: 'title',
				right: 'month,agendaWeek,agendaDay'
			},
			editable: true,
			selectable: true,
			selectHelper: true,
			events: function(start, end, callback) {
				wn.call({
					method: 'utilities.page.calendar.calendar.get_events',
					type: "GET",
					args: {
						start: dateutil.obj_to_str(start),
						end: dateutil.obj_to_str(end),
						company: wn.user.get_default("company")[0],
						employee: wn.user.get_default("employee")[0]
					},
					callback: function(r) {
						var events = r.message;
						$.each(events, function(i, d) { 
							d.editable = d.owner==user;
							var options = erpnext.calendar.event_options[d.doctype];
							if(options && options.prepare)
								options.prepare(d);
						});
						callback(events);
					}
				})
			},
			eventClick: function(event, jsEvent, view) {
				// edit event description or delete
				var options = erpnext.calendar.event_options[event.doctype];
				if(options && options.click)
					options.click(event);
			},
			eventDrop: function(event, dayDelta, minuteDelta, allDay, revertFunc) {
				erpnext.calendar.update_event(event);
			},
			eventResize: function(event, dayDelta, minuteDelta, allDay, revertFunc) {
				erpnext.calendar.update_event(event);
			},
			select: function(startDate, endDate, allDay, jsEvent, view) {
				if(jsEvent.day_clicked && view.name=="month")
					return;
				var event = wn.model.get_new_doc("Event");
				event.starts_on = wn.datetime.get_datetime_as_string(startDate);
				event.ends_on = wn.datetime.get_datetime_as_string(endDate);
				event.all_day = allDay ? 1 : 0;
				wn.set_route("Form", "Event", event.name);
			},
			dayClick: function(date, allDay, jsEvent, view) {
				jsEvent.day_clicked = true;
				$("#fullcalendar").fullCalendar("gotoDate", date)
				return false;
			}
		});
	});

	wrapper.setup_complete = true;
	
}

erpnext.calendar.update_event = function(event) {
	wn.model.remove_from_locals("Event", event.id);
	wn.call({
		module: "utilities",
		page: "calendar",
		method: "update_event",
		args: {
			"start": wn.datetime.get_datetime_as_string(event.start),
			"end": wn.datetime.get_datetime_as_string(event.end),
			"all_day": event.allDay,
			"name": event.id
		},
		callback: function(r) {
			if(r.exc) {
				show_alert("Unable to update event.")
			}
		}
	});
}

erpnext.calendar.event_options = {
	"Leave Block List Date": {
		prepare: function(d) {
			d.color = "#aaa";
		}
	},
	"Event": {
		prepare: function(d) {
			if(d.event_type=="Public") {
				d.color = "#57AF5B";
			}
		},
		click: function(event) {
			wn.set_route("Form", "Event", event.id);
		}
	},
	"Leave Application": {
		prepare: function(d) {
			d.color = "#4F9F96";
		},
		click: function(event) {
			if(event.employee==wn.user.get_default("employee")[0]) {
				wn.set_route("Form", "Leave Application", event.id);
			}
		}
	}
}

