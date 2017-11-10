frappe.provide('frappe.desktop');

frappe.model.get_value("HR Settings", "HR", "checkin_check_out",
    function(d) {
        if(parseInt(d.checkin_check_out)){
            frappe.call({
                method: "erpnext.hr.doctype.attendance.attendance.validate_attendance",
                callback: function(r) {
                    if (!r.message) {
                        show_popup();
                    }
                }
            });
        }
    });


function show_popup() {
    var dialog = new frappe.ui.Dialog({
        title: __("Check-in Attendance "),
        body: __("Confirm"),
        fields: [
          {"fieldtype": "Button", "label": __("Check-In"), "fieldname": "check_in"},
        ]
    });

    dialog.fields_dict.check_in.$input.click(function() {
        frappe.call({
            method: "erpnext.hr.doctype.attendance.attendance.check_in",
            callback: function(r) {
                if (r.message) {
                    dialog.hide();
                }
            }
        });
    });

    dialog.show();
}
