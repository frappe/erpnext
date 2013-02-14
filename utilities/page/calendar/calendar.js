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
	wn.ui.make_app_page({
		parent: wrapper,
		single_column: true,
		title: 'Calendar'
	});
	
	wn.require('lib/js/lib/fullcalendar/fullcalendar.css');
	wn.require('lib/js/lib/fullcalendar/fullcalendar.js');
}

pscript.update_event = function(event) {
	wn.model.remove_from_locals("Event", event.id);
	wn.call({
		module: "utilities",
		page: "calendar",
		method: "update_event",
		args: {
			"start": wn.datetime.get_datetime_as_string(event.start),
			"end": wn.datetime.get_datetime_as_string(event.end),
			"name": event.id
		},
		callback: function(r) {
			if(r.exc) {
				show_alert("Unable to update event.")
			}
		}
	});
}


pscript.onshow_calendar = function(wrapper) {
	if(!wrapper.setup_complete) {
		$('<div id="fullcalendar">').appendTo($(wrapper).find('.layout-main')).fullCalendar({
			header: {
				left: 'prev,next today',
				center: 'title',
				right: 'month,agendaWeek,agendaDay'
			},
			editable: true,
			events: function(start, end, callback) {
				wn.call({
					method: 'utilities.page.calendar.calendar.get_events',
					type: "GET",
					args: {
						start: dateutil.obj_to_str(start),
						end: dateutil.obj_to_str(end)
					},
					callback: function(r) {
						var events = r.message;
						$.each(events, function(i, d) { 
							d.editable = d.owner==user;
							d.allDay = false; 
						});
						callback(events);
					}
				})
			},
			dayClick: function(date, allDay, jsEvent, view) {
				// if current date, show popup to create a new event
				var ev = wn.model.create('Event')
				ev.doc.set('start', date);
				ev.doc.set('end', new Date(date));
				ev.doc.set('all_day', 1);

			},
			eventClick: function(calEvent, jsEvent, view) {
				// edit event description or delete
				wn.set_route("Form", "Event", calEvent.id);
			},
			eventDrop: function(event, dayDelta, minuteDelta, allDay, revertFunc) {
				pscript.update_event(event);
			},
			eventResize: function(event, dayDelta, minuteDelta, allDay, revertFunc) {
				pscript.update_event(event);
			}
		});

		wrapper.setup_complete = true;
	} else {
		$("#fullcalendar").fullCalendar("refetchEvents");
	}
}

