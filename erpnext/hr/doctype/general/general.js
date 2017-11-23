// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('General', {
    refresh: function(frm) {

    },
    onload: function(frm) {
        var user_id = String(frappe.session.user_email);


        // dummy user for testing 
        user_id = "aa.alsulaiteen@tawari.sa"

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                'doctype': 'Employee',
                'filters': { 'user_id': user_id },
                'fieldname': [
                    'name',
                    'employee_name',
                    'employee_name_english',
                    'date_of_joining',
                    'date_of_birth',
                    'emp_nationality',
                    'gosi_subscription_no',
                    'civil_id',
                ]
            },
            freeze: true,
            callback: function(r) {
                if (!r.exc) {
                    // alert(r);
                    cur_frm.doc.employee = r.message.name; // Test fix for automatic employee field being set.
                    cur_frm.doc.english_name = r.message.employee_name_english;
                    cur_frm.doc.arabic_name = r.message.employee_name;
                    cur_frm.doc.civil_id = r.message.civil_id;
                    cur_frm.doc.gosi = r.message.gosi_subscription_no;
                    cur_frm.doc.dob = r.message.date_of_birth;
                    cur_frm.doc.joining_date = r.message.date_of_joining;
                    cur_frm.doc.nationality = r.message.emp_nationality;
                    refresh_many(['employee', 'english_name', 'arabic_name', 'civil_id', 'gosi', 'dob', 'joining_date', 'nationality']);
                    frm.trigger("load_internal_work_history");
                    frm.trigger("load_education");
                    frm.trigger("load_training");
                    frm.trigger("seminars");
                    frm.trigger("employee_slip_name");


                }
            }
        });




    },
    load_internal_work_history: function() {

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Employee Internal Work History',
                'filters': { 'parent': cur_frm.doc.employee },
                'fields': [
                    'branch',
                    'department',
                    'designation',
                    'grade',
                    'level',
                    'from_date',
                    'to_date'
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("internal_work_history");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['internal_work_history']);
                }
            }
        });

    },
    load_education: function() {

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Employee Education',
                'filters': { 'parent': cur_frm.doc.employee },
                'fields': [
                    'school_univ',
                    'qualification',
                    'level',
                    'year_of_passing',
                    'class_per',
                    'location',
                    'maj_opt_subj'
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("academic_education");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['academic_education']);
                }
            }
        });

    },
    load_training: function() {

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Profissonal Training',
                'filters': { 'parent': cur_frm.doc.employee },
                'fields': [
                    'cource',
                    'start_from',
                    'ended_on',
                    'location',
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("profissonal_training");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['profissonal_training']);
                }
            }
        });

    },
    seminars: function() {

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Conference And Seminars',
                'filters': { 'parent': cur_frm.doc.employee },
                'fields': [
                    'title',
                    'location',
                    'start',
                    'end',
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("seminars");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['seminars']);
                }
            }
        });

    },
    employee_slip_name: function() {

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Salary Slip',
                'filters': { 'employee': cur_frm.doc.employee },
                'fields': [
                    'name',
                    'total_deduction',
                    'gross_pay',
                    'net_pay'
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                    cur_frm.doc.sal_slip= r.message[0].name;
                    cur_frm.doc.deductions_total = r.message[0].total_deduction;
                    cur_frm.doc.earning_total = r.message[0].gross_pay;
                    cur_frm.doc.net_monthly_income = r.message[0].net_pay;

                    refresh_many(['sal_slip','deductions_total','earning_total','net_monthly_income']);

                    cur_frm.trigger("get_salay_component_deductions");
                    cur_frm.trigger("get_salay_component_earnings");


                }
            }
        });

    },
     get_salay_component_deductions: function() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Salary Detail',
                'filters': { 'parent': cur_frm.doc.sal_slip,'parentfield ':'deductions' },
                'fields': [
                    'salary_component',
                    'amount',
                    'depends_on_lwp',
                    'abbr',
                    'formula'
                    
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                	console.log(r.message);
                	console.log(r.message.length);
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("deductions");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['deductions']);
                }
            }
        });

    },
     get_salay_component_earnings: function() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Salary Detail',
                'filters': { 'parent': cur_frm.doc.sal_slip,'parentfield ':'earnings' },
                'fields': [
                    'salary_component',
                    'amount',
                    'depends_on_lwp',
                    'abbr',
                    'formula'
                    
                ]
            },
            callback: function(r) {
                if (!r.exc) {
                	console.log(r.message);
                	console.log(r.message.length);
                    for (var i = 0; i < r.message.length; i++) {
                        var d = cur_frm.add_child("earnings");
                        var item = r.message[i];
                        for (var key in item) {
                            if (!is_null(item[key])) {
                                d[key] = item[key];
                            }
                        }
                    }
                    refresh_many(['earnings']);
                }
            }
        });

    },


});



// cur_frm.add_custom_button("Open Something", function(){
//     frappe.set_route(["query-report", "Some Report"]);
// });

frappe.ui.form.on("General", "attendance", function(frm) {
    frappe.set_route(["query-report", "Attendance"]);
});



// frappe.ui.form.on("POS Profile", "button_name", function(frm) {

// frappe.call({
//     method: 'erpnext.accounts.doctype.pos_profile.pos_profile.get_cach',
//     args: {
//         'pos_profile': cur_frm.doc.name,
//         'date': frappe.boot.server_date
//     },
//     callback: function(r) {
//         if (!r.exc) {
//             // code snippet
//             console.log(r.message);
//             frm.doc.sales_amount=r.message
//             cur_frm.refresh_field("sales_amount");
//             var income = frm.doc.sales_amount + frm.doc.cash_drawer;
//             var rm_cache = frm.doc.remove_cach;
//             var closing_cach = income - rm_cache;
//             frm.doc.closing_cach=closing_cach
//             cur_frm.refresh_field("closing_cach");

//             // alert(r.message.total);
//         }
//     }
// });

// });