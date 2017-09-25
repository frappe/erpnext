// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meeting", "refresh", function(frm) {
	frm.add_custom_button(__("Send Email"), function() {
		if (frm.doc.status==="Planned") {
			frappe.call({
				method: "erpnext.meeting_minutes.api.send_invitation_emails",
				args: {
					meeting: frm.doc.name
				}
			});
		}
	});

    });

frappe.ui.form.on("Meeting Attendee", {
	attendee: function(frm, cdt, cdn) {
		var attendee = frappe.model.get_doc(cdt, cdn);
		if (attendee.attendee) {
			// if attendee, get full name
			frappe.call({
				method: "erpnext.meeting_minutes.doctype.meeting.meeting.get_full_name",
				args: {
					attendee: attendee.attendee
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, "full_name", r.message);
				}
			});

		} else {
			// if no attendee, clear full name
			frappe.model.set_value(cdt, cdn, "full_name", null);
		}
	},
});
