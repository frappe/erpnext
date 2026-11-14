// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Video", {
	refresh: function (frm) {
		frm.events.toggle_youtube_statistics_section(frm);
		frm.add_custom_button(__("Watch Video"), () => frm.events.watch_video(frm));
	},

	watch_video: (frm) => {
		if (frm.doc.provider === "YouTube") {
			frappe.help.show_video(frm.doc.youtube_video_id, frm.doc.title);
		} else {
			open_external_video(frm.doc.url);
		}
	},

	toggle_youtube_statistics_section: (frm) => {
		if (frm.doc.provider === "YouTube") {
			frappe.db.get_single_value("Video Settings", "enable_youtube_tracking").then((val) => {
				frm.toggle_display("youtube_tracking_section", val);
			});
		}
	},
});

function open_external_video(value) {
	let url;
	try {
		url = new URL(value);
	} catch {
		url = null;
	}

	if (!["http:", "https:"].includes(url?.protocol)) {
		frappe.throw(__("Invalid video URL"));
	}
	window.open(url.href, "_blank", "noopener");
}
