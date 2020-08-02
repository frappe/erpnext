// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Video', {
	refresh: function (frm) {
		if (frm.doc.provider === "YouTube") {
			frappe.db.get_single_value("Video Settings", "enable_youtube_tracking").then(value => {
				if (value) {
					frm.events.get_video_stats(frm);
				} else {
					frm.set_df_property('youtube_tracking_section', 'hidden', true);
				}
			});
		}

		frm.add_custom_button("Watch Video", () => frappe.help.show_video(frm.doc.url, frm.doc.title));
	},

	get_video_stats: (frm) => {
		const expression = '(?:youtube.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu.be/)([^"&?\\s]{11})';
		var youtube_id = frm.doc.url.match(expression)[1];

		frappe.call({
			method: "erpnext.utilities.doctype.video.video.update_video_stats",
			args: {
				youtube_id: youtube_id
			},
			callback: (r) => {
				var result = r.message;
				var fields = ['like_count', 'view_count', 'dislike_count', 'comment_count'];
				fields.forEach((field) => {
					frm.doc[field] = result[field];
				})
				frm.refresh_fields();
			}
		});
	}
});
