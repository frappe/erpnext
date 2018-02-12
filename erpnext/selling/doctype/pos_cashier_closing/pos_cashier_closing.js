// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Cashier Closing', {

    set_reconciliation_difference: function(frm) {
        if (frm.doc.actual_sales_amount > frm.doc.drawer_sales_amount) {
            net_val = frm.doc.actual_sales_amount - frm.doc.drawer_sales_amount;
        } else {
            net_val = frm.doc.drawer_sales_amount - frm.doc.actual_sales_amount;
        }
        if (net_val == 0) {
            frm.set_value("reconciliation_difference", net_val);
        } else {
            frm.set_value("reconciliation_difference", net_val);
        }
    },

    set_drawer_sales_amount: function(frm) {
        if (frm.doc.opening_balance != undefined && frm.doc.closing_balance == undefined) {
            frm.set_value("drawer_sales_amount", frm.doc.opening_balance);
        }
        if (frm.doc.opening_balance == undefined && frm.doc.closing_balance != undefined) {
            frm.set_value("drawer_sales_amount", frm.doc.closing_balance);
        }
        if (frm.doc.opening_balance != undefined && frm.doc.closing_balance != undefined) {
            if (frm.doc.closing_balance > frm.doc.opening_balance) {
                diff = frm.doc.closing_balance - frm.doc.opening_balance;
            } else {
                diff = frm.doc.opening_balance - frm.doc.closing_balance;
            }
            frm.set_value("drawer_sales_amount", diff);
        }
    },

    get_pos_sales_total: function(frm) {
        frm.set_value("actual_sales_amount", 0.0);
        frappe.call({
            method: "erpnext.selling.doctype.pos_cashier_closing.pos_cashier_closing.get_pos_sales_total",
            args: {
                from_date: frm.doc.start_date,
                to_date: frm.doc.close_date,
                from_time: frm.doc.start_time,
                to_time: frm.doc.close_time,
                owner: frm.doc.user
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value("actual_sales_amount", r.message);
                }
            }
        });

    },

    actual_sales_amount: function(frm) {
        frm.events.set_reconciliation_difference(frm);
    },
    drawer_sales_amount: function(frm) {
        frm.events.set_reconciliation_difference(frm);
    },
    opening_balance: function(frm) {
        frm.events.set_drawer_sales_amount(frm);
    },
    closing_balance: function(frm) {
        frm.events.set_drawer_sales_amount(frm);
    },

    onload: function(frm) {
        //value setup
        if (frm.doc.shift == undefined) {
            frm.set_value("start_time", "");
            frm.set_value("close_time", "");
        }
        if (frm.doc.user == undefined) {
            frm.set_value("user", frappe.user.name);
        }
        if (frm.doc.start_date == undefined) {
            frm.set_value("start_date", frappe.datetime.get_today());
        }
        if (frm.doc.close_date == undefined) {
            frm.set_value("close_date", frappe.datetime.get_today());
        }
        if (frm.doc.opening_balance == undefined && frm.doc.closing_balance == undefined) {
            frm.set_value("drawer_sales_amount", 0);
        }
    },

    refresh: function(frm) {
        frm.add_custom_button(__('Reconciliation'),
            function() {
                frm.events.get_pos_sales_total(frm);
            }
        );
    },

    validate: function(frm, cdt, cd) {
        if (frm.doc.start_date == undefined || frm.doc.user == undefined || frm.doc.shift == undefined || frm.doc.opening_balance == undefined) {
            frappe.throw(__("Please fill mandatory fields"));
            frappe.validated = false;
            return false
        } else {
            frappe.call({
                method: "erpnext.selling.doctype.pos_cashier_closing.pos_cashier_closing.check_POS_duplicate",
                args: {
                    doc_name: frm.doc.name,
                    start_date: frm.doc.start_date,
                    shift: frm.doc.shift,
                    owner: frm.doc.user
                },
                callback: function(r) {
                    if (r.message > 0) {
                        frm.set_value("start_date", "");
                        frm.set_value("shift", "");
                        frappe.throw(__("Duplicate record"));
                        frappe.validated = false;
                        return false
                    } else {
                        //success , no duplicate"                        
                        frm.events.get_pos_sales_total(frm);
                    }
                }
            });
        }
    }
});

cur_frm.add_fetch("shift", "start_time", "start_time");
cur_frm.add_fetch("shift", "end_time", "close_time");