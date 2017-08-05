// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");
// cur_frm.add_fetch("employee", "grade", "grade");
// cur_frm.add_fetch("grade", "internal_per_diem_rate", "internal_per_diem_rate");
// cur_frm.add_fetch("grade", "external_per_diem_rate", "external_per_diem_rate");
// cur_frm.add_fetch("grade", "internal_ticket_class", "internal_ticket_class");
// cur_frm.add_fetch("grade", "external_ticket_class", "external_ticket_class");
cur_frm.cscript.custom_grade = function(doc, cdt, cd) {
    // console.log(cd);
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Grade",
            fieldname: ["internal_per_diem_rate", "external_per_diem_rate"],
            filters: { name: doc.grade }
        },
        callback: function(r) {
            cur_frm.set_value("external_per_diem_rate", r.message.external_per_diem_rate);
            cur_frm.set_value("internal_per_diem_rate", r.message.internal_per_diem_rate);
        }
    });
    // var ss = frappe.model.get_value("Job Assignment", doc.grade, "internal_per_diem_rate");
    // console.log(r);
    // cur_frm.refresh_fields(['days', 'internal_assignment', 'external_assignment', 'cost_total', 'internal_per_diem_rate', 'external_per_diem_rate',
    //     'internal_ticket_class', 'external_ticket_class'
    // ]);
};
frappe.ui.form.on('Job Assignment', {
    refresh: function(frm) {},
    onload: function(frm) {
        // frm.set_query("reports_to", function() {
        //     return {
        //         query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
        //         filters: {
        //             employee: frm.doc.employee
        //         }
        //     };
        // });
    }
});

cur_frm.cscript.custom_assignment_type =
    cur_frm.cscript.custom_employee = function(doc, cdt, cd) {
        // get_grade_info(cur_frm);
        cur_frm.set_value("city", "");
        if (doc.assignment_type === 'Internal Assign') {
            cur_frm.set_query("city", function() {
                return {
                    filters: [
                        ["City", "location", "=", "Internal"]
                    ]
                };
            });
        }
        if (doc.assignment_type === 'External Assign') {
            cur_frm.set_query("city", function() {
                return {
                    filters: [
                        ["City", "location", "=", "External"],
                    ]
                };
            });
        }
        // get_number_of_leave_days(cur_frm);
    };
cur_frm.cscript.custom_external_city_type = cur_frm.cscript.custom_world_countries = function(doc, cdt, cd) {
    // get_grade_info(cur_frm);
    cur_frm.set_value("city", "");
    cur_frm.fields_dict.city.get_query = function(doc) {
        return {
            filters: [
                ['external_city_type', '=', doc.external_city_type],
                ['world_countries', '=', doc.world_countries]
            ]
        };
    };
};
cur_frm.fields_dict.city.get_query = function(doc) {
    return {
        filters: [
            ['external_city_type', '=', doc.external_city_type],
            ['world_countries', '=', doc.world_countries]
        ]
    };
};
// cur_frm.cscript.custom_other_costs =
//     cur_frm.cscript.custom_training_cost =
//     cur_frm.cscript.custom_accommodation_cost =
//     cur_frm.cscript.custom_living_costs =
//     cur_frm.cscript.custom_transportation_costs =
//     cur_frm.cscript.custom_ticket_cost =
//     cur_frm.cscript.custom_visa_cost = function(doc, cdt, cd) {
//         get_grade_info(cur_frm);
//     };
cur_frm.cscript.custom_from_date =
    cur_frm.cscript.custom_to_date =
    cur_frm.cscript.ticket_cost =
    cur_frm.cscript.internal_per_diem_rate =
    cur_frm.cscript.external_per_diem_rate =
    // cur_frm.cscript.custom_employee =
    cur_frm.cscript.custom_assignment_type = function() {
        frappe.call({
            doc: cur_frm.doc,
            method: "get_number_of_leave_days",
            callback: function(r) {
                cur_frm.refresh_fields(['days', 'internal_assignment', 'external_assignment', 'cost_total', 'internal_per_diem_rate', 'external_per_diem_rate',
                    'internal_ticket_class', 'external_ticket_class'
                ]);
                frappe.call({
                    doc: cur_frm.doc,
                    method: "get_ja_cost",
                    callback: function(r) {
                        cur_frm.refresh_fields(['cost_total', 'total']);
                    }
                });
            }
        });

    };
// cur_frm.cscript.internal_per_diem_rate = function(){
//     alert("ff");
//     // frappe.call({
//     //             doc: cur_frm.doc,
//     //             method: "get_ja_cost",
//     //             callback: function(r) {
//     //                 cur_frm.refresh_fields(['cost_total', 'total']);
//     //             }
//     //         });
// }
// fields = {_('Other Costs'):self.other_costs,
// _('Training Cost'):self.training_cost,
// _('Accommodation Cost'):self.accommodation_cost,
// _('Living Costs'):self.living_costs,
// _('Transportation Costs'):self.transportation_costs,
// _('Ticket Costs'):self.ticket_cost,
// _('VISA Cost'):self.visa_cost



var get_number_of_leave_days = function(frm) {
    frappe.call({
        doc: frm.doc,
        method: "get_number_of_leave_days",
        callback: function(r) {
            //~ refresh_many(['days', 'internal_assignment', 'external_assignment', 'cost_total']);
            frm.refresh_fields(['days', 'internal_assignment', 'external_assignment', 'cost_total', 'internal_per_diem_rate', 'external_per_diem_rate',
                'internal_ticket_class', 'external_ticket_class'
            ]);
            // console.log(r);
        }
    });
};
var get_grade_info = function(frm) {
    frappe.call({
        doc: frm.doc,
        method: "get_grade_info",
        callback: function(r) {
            console.log(r);
            //~ refresh_many(['days', 'internal_assignment', 'external_assignment', 'cost_total']);
            //~ frm.refresh_fields(['days', 'internal_assignment', 'external_assignment', 'cost_total']);
            frm.refresh_fields(['days', 'internal_assignment', 'external_assignment', 'cost_total', 'internal_per_diem_rate', 'external_per_diem_rate',
                'internal_ticket_class', 'external_ticket_class'
            ]);
        }
    });
};
var numbers_only_fields = ["other_costs",
    "training_cost",
    "accommodation_cost",
    "living_costs",
    "transportation_costs",
    "ticket_cost",
    "visa_cost"
];

$.each(numbers_only_fields, function(index, value) {
    $('[data-fieldname=' + value + ']').on('keypress', numbersonly);
});

function numbersonly(e) {
    var unicode = e.charCode ? e.charCode : e.keyCode;
    if (unicode != 8) { //if the key isn't the backspace key (which we should allow)
        if (unicode < 46 || unicode > 57) //if not a number
            return false; //disable key press
    }
}
