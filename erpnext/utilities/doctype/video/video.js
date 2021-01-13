// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Video', {
	refresh: function (frm) {
		frm.events.toggle_youtube_statistics_section(frm);
		frm.add_custom_button("Watch Video", () => frappe.help.show_video(frm.doc.url, frm.doc.title));
	},

	toggle_youtube_statistics_section: (frm) => {
		if (frm.doc.provider === "YouTube") {
			frappe.db.get_single_value("Video Settings", "enable_youtube_tracking").then( val => {
				frm.toggle_display("youtube_tracking_section", val);
			});
		}
	}
});
