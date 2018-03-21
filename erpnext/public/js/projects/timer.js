frappe.provide("erpnext.timesheet")

erpnext.timesheet.timer = function(frm, row, timestamp=0) {
	let dialog = new frappe.ui.Dialog({
		title: __("Timer"),
		fields:
		[
			{"fieldtype": "Link", "label": __("Activity Type"), "fieldname": "activity_type",
				"reqd": 1, "options": "Activity Type"},
			{"fieldtype": "Link", "label": __("Project"), "fieldname": "project", "options": "Project"},
			{"fieldtype": "Float", "label": __("Expected Hrs"), "fieldname": "expected_hours"},
			{"fieldtype": "Section Break"},
			{"fieldtype": "HTML", "fieldname": "timer_html"}
		]
	});

	if (row) {
		dialog.set_values({
			'activity_type': row.activity_type,
			'project': row.project,
			'expected_hours': row.expected_hours
		});
	}
	dialog.get_field("timer_html").$wrapper.append(frappe.render_template("timesheet"));
	control_timer(frm, dialog, row, timestamp);
	dialog.show();
}

var control_timer = function(frm, dialog, row, timestamp=0) {
	var $btn_start = $(".playpause .btn-start");
	var $btn_complete = $(".playpause .btn-complete");
	var interval = null;
	var currentIncrement = timestamp
	var isPaused = false;
	var initialised = row ? true : false;
	var clicked = false;
	var paused_time = 0;

	// If row with not completed status, initialize timer with the time elapsed on click of 'Start Timer'.
	if (row) {
		initialised = true;
		$btn_start.hide();
		$btn_complete.show();
		initialiseTimer();
	}
	if (!initialised) {
		$btn_complete.hide();
	}
	$btn_start.click(function(e) {
		if (!initialised) {
			// New activity if no activities found
			var args = dialog.get_values();
			if(!args) return;
			if (!frm.doc.time_logs[0].activity_type) {
				frm.doc.time_logs = [];
			}
			row = frappe.model.add_child(frm.doc, "Timesheet Detail", "time_logs");
			row.activity_type = args.activity_type;
			row.from_time = frappe.datetime.get_datetime_as_string();
			row.expected_hours = args.expected_hours;
			row.completed = 0;
			let d = moment(row.from_time)
			if(row.expected_hours) {
				d.add(row.expected_hours, "hours");
				row.to_time = d.format(moment.defaultDatetimeFormat);
			}
			frm.refresh_field("time_logs");
			frm.save();
		}

		if (clicked) {
			e.preventDefault();
			return false;
		}

		if (!initialised) {
			initialised = true;
			isPaused = false;
			$btn_start.hide();
			$btn_complete.show();
			initialiseTimer();
		}
	});

	// Stop the timer and update the time logged by the timer on click of 'Complete' button
	$btn_complete.click(function() {
		var grid_row = cur_frm.fields_dict['time_logs'].grid.grid_rows_by_docname[row.name];
		var args = dialog.get_values();
		grid_row.doc.completed = 1;
		grid_row.doc.activity_type = args.activity_type;
		grid_row.doc.project = args.project;
		grid_row.doc.expected_hours = args.expected_hours;
		grid_row.doc.hours = currentIncrement / 3600;
		grid_row.doc.to_time = frappe.datetime.now_datetime();
		grid_row.refresh();
		frm.save();
		reset();
		dialog.hide();
	})
	function initialiseTimer() {
		interval = setInterval(function() {
			if (isPaused) return;
			var current = setCurrentIncrement();
			updateStopwatch(current);
		}, 1000);
	}

	function updateStopwatch(increment) {
		var hours = Math.floor(increment / 3600);
		var minutes = Math.floor((increment - (hours * 3600)) / 60);
		var seconds = increment - (hours * 3600) - (minutes * 60);

		// If modal is closed by clicking anywhere outside, reset the timer
		if (!$('.modal-dialog').is(':visible')) {
			reset();
		}
		if(hours > 99)
		reset();
		$(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
		$(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
		$(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
	}

	function setCurrentIncrement() {
		currentIncrement += 1;
		return currentIncrement;
	}

	function reset() {
		currentIncrement = 0;
		isPaused = true;
		initialised = false;
		clearInterval(interval);
		$(".hours").text("00");
		$(".minutes").text("00");
		$(".seconds").text("00");
		$btn_complete.hide();
		$btn_start.show();
	}
}