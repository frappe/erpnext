// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Call Log', {
	refresh: function(frm) {
		frm.events.setup_recording_audio_control(frm);
		const incoming_call = frm.doc.type == 'Incoming';
		frm.add_custom_button(incoming_call ? __('Callback'): __('Call Again'), () => {
			const number = incoming_call ? frm.doc.from : frm.doc.to;
			frappe.phone_call.handler(number, frm);
		});
	},
	setup_recording_audio_control(frm) {
		const recording_wrapper = frm.get_field('recording_html').$wrapper;
		if (!frm.doc.recording_url || frm.doc.recording_url == 'null') {
			recording_wrapper.empty();
		} else {
			recording_wrapper.addClass('input-max-width');
			recording_wrapper.html(`
				<audio
					controls
					src="${frm.doc.recording_url}">
				</audio>
			`);
		}
	}
});
