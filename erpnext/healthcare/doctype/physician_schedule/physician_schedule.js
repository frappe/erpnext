// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physician Schedule', {
	refresh: function(frm) {
		frm.add_custom_button(__('Add Time Slots'), () => {
			var d = new frappe.ui.Dialog({
				fields: [
					{fieldname: 'day', label: __('Day'), fieldtype:'Select',
						options:[
							{value:'Sunday', label:__('Sunday')},
							{value:'Monday', label:__('Monday')},
							{value:'Tuesday', label:__('Tuesday')},
							{value:'Wednesday', label:__('Wednesday')},
							{value:'Thursday', label:__('Thursday')},
							{value:'Friday', label:__('Friday')},
							{value:'Saturday', label:__('Saturday')},
						], reqd: 1, 'default': 'Monday'},
					{fieldname: 'from_time', label:__('From'), fieldtype:'Time',
						'default': '09:00:00', reqd: 1},
					{fieldname: 'to_time', label:__('To'), fieldtype:'Time',
						'default': '12:00:00', reqd: 1},
					{fieldname: 'duration', label:__('Appointment Duration (mins)'),
						fieldtype:'Int', 'default': 15, reqd: 1},
				],
				primary_action_label: __('Add Timeslots'),
				primary_action: () => {
					var values = d.get_values();
					if(values) {
						let cur_time = moment(values.from_time, 'HH:mm:ss');
						let end_time = moment(values.to_time, 'HH:mm:ss');


						while(cur_time < end_time) {
							let to_time = cur_time.clone().add(values.duration, 'minutes');
							if(to_time <= end_time) {

								// add a new timeslot
								frm.add_child('time_slots', {
									from_time: cur_time.format('HH:mm:ss'),
									to_time: to_time.format('HH:mm:ss'),
									day: values.day
								});
							}
							cur_time = to_time;
						}

						frm.refresh_field('time_slots');
						frappe.show_alert({
							message:__('Time slots added'),
							indicator:'green'
						});
					}
				},
			});
			d.show();
		});
	}
});
