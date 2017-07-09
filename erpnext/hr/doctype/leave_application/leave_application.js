// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'reports_to', 'leave_approver');

frappe.ui.form.on("Leave Application", {
    validate: function(frm) {
        if (!frm.doc.__islocal && frm.doc.owner != frappe.session.user) {
            if (frm.doc.leave_approver != frappe.session.user && frm.doc.docstatus != 1) {
                //~ frm.set_value("docstatus", 0);
                cur_frm.doc.docstatus = 0
                frm.set_value("workflow_state", "Pending");
                alert("Hit");
            } else {
                alert("No");
            }
        }

    },
    onload: function(frm) {


        if (!frm.doc.posting_date) {
            frm.set_value("posting_date", get_today());
        }

        frm.set_query("leave_approver", function() {
            return {
                query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
                filters: {
                    employee: frm.doc.employee
                }
            };
        });

        frm.set_query("employee", erpnext.queries.employee);

    },

    refresh: function(frm) {
        if (frm.doc.docstatus == 1 && frm.doc.is_returned == 0) {
            if (frm.doc.from_date <= get_today() && frm.doc.to_date >= get_today()) {
                frm.add_custom_button(__("Cancel Leave Application"), function() {
                    // frappe.route_options = { "integration_request_service": "Razorpay" };
                    frappe.set_route("Form", "Cancel Leave Application", "New Cancel Leave Application 1");
                });
            }
            if (frm.doc.to_date < get_today()) {
                frm.add_custom_button(__("Return From Leave Statement"), function() {
                    // frappe.route_options = { "integration_request_service": "Razorpay" };
                    frappe.set_route("Form", "Return From Leave Statement", "New Return From Leave Statement 1");
                });
            }
        }
        if (frm.is_new()) {
            frm.set_value("status", "Open");
            frm.trigger("calculate_total_days");
        }
    },

    leave_approver: function(frm) {

        if (frm.doc.leave_approver) {
            frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
        }
    },

    employee: function(frm) {
        frm.trigger("get_leave_balance");
    },

    leave_type: function(frm) {
        frm.trigger("get_leave_balance");
    },

    half_day: function(frm) {
        if (frm.doc.from_date) {
            frm.set_value("to_date", frm.doc.from_date);
            frm.trigger("calculate_total_days");
        }
    },

    from_date: function(frm) {
        if (cint(frm.doc.half_day) == 1) {
            frm.set_value("to_date", frm.doc.from_date);
        }
        frm.trigger("calculate_total_days");
    },

    to_date: function(frm) {
        if (cint(frm.doc.half_day) == 1 && cstr(frm.doc.from_date) && frm.doc.from_date != frm.doc.to_date) {
            msgprint(__("To Date should be same as From Date for Half Day leave"));
            frm.set_value("to_date", frm.doc.from_date);
        }

        frm.trigger("calculate_total_days");
    },

    get_leave_balance: function(frm) {
        if (frm.doc.docstatus == 0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date) {
            return frappe.call({
                method: "erpnext.hr.doctype.leave_application.leave_application.get_leave_balance_on",
                args: {
                    employee: frm.doc.employee,
                    date: frm.doc.from_date,
                    leave_type: frm.doc.leave_type,
                    consider_all_leaves_in_the_allocation_period: true
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frm.set_value('leave_balance', r.message);
                    }
                }
            });
        }
    },

    calculate_total_days: function(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            if (cint(frm.doc.half_day) == 1) {
                frm.set_value("total_leave_days", 0.5);
            } else if (frm.doc.employee && frm.doc.leave_type) {
                // server call is done to include holidays in leave days calculations
                return frappe.call({
                    method: 'erpnext.hr.doctype.leave_application.leave_application.get_number_of_leave_days',
                    args: {
                        "employee": frm.doc.employee,
                        "leave_type": frm.doc.leave_type,
                        "from_date": frm.doc.from_date,
                        "to_date": frm.doc.to_date,
                        "half_day": frm.doc.half_day
                    },
                    callback: function(r) {
                        if (r && r.message) {
                            frm.set_value('total_leave_days', r.message);
                            frm.set_value('remaining_leave_days', parseFloat(frm.doc.leave_balance) - parseFloat(r.message));

                            frm.trigger("get_leave_balance");
                        }
                    }
                });
            }
        }
    },

});
