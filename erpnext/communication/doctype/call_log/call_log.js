// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Call Log', {
	refresh: function(frm) {
		frm.events.setup_recording_audio_control(frm);
	},
	setup_recording_audio_control(frm) {
		const recording_wrapper = frm.get_field('recording_html').$wrapper;
		if (!frm.doc.recording_url || frm.doc.recording_url == 'null') {
			recording_wrapper.empty();
		} else {
			recording_wrapper.addClass('input-max-width');
			recording_wrapper.html(`
				<audio
					style="width: 100%"
					controls
					src="${frm.doc.recording_url}">
						Your browser does not support the
						<code>audio</code> element.
				</audio>
			`);
		}
	}
});
