// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Type', {
	refresh: function(frm) {
		frm.add_custom_button(
			__('Mark Attendance'),
			() => {
				if (!frm.doc.enable_auto_attendance) {
					frm.scroll_to_field('enable_auto_attendance');
					frappe.throw(__('Please Enable Auto Attendance and complete the setup first.'));
				}

				if (!frm.doc.process_attendance_after) {
					frm.scroll_to_field('process_attendance_after');
					frappe.throw(__('Please set {0}.', [__('Process Attendance After').bold()]));
				}

				if (!frm.doc.last_sync_of_checkin) {
					frm.scroll_to_field('last_sync_of_checkin');
					frappe.throw(__('Please set {0}.', [__('Last Sync of Checkin').bold()]));
				}

				frm.call({
					doc: frm.doc,
					method: 'process_auto_attendance',
					freeze: true,
					callback: () => {
						frappe.msgprint(__('Attendance has been marked as per employee check-ins'));
					}
				});
			}
		);
	}
});
