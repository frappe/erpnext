// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Training Trip', {
// 	refresh: function(frm) {

// 	}
// });




cur_frm.add_fetch("employee", "employee_name", "employee_name");
cur_frm.add_fetch('employee','department','department');
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
   

};
frappe.ui.form.on('Training Trip', {
    refresh: function(frm) {},
    workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
        if (cur_frm.doc.handled_by=="Director" && cur_frm.doc.assignment_type=="Internal" && cur_frm.doc.days>=5 ){
            cur_frm.doc.workflow_state = "Approved By Director(CEO+INT)"
        }else if(cur_frm.doc.handled_by=="Director" && cur_frm.doc.assignment_type=="External" && cur_frm.doc.days>=5 ){
            cur_frm.doc.workflow_state = "Approved By Director(CEO+X)"
        }else if(cur_frm.doc.handled_by=="Director" && cur_frm.doc.assignment_type=="Internal"){
            cur_frm.doc.workflow_state = "Approved By Director(INT)"
        }else if(cur_frm.doc.handled_by=="Director" && cur_frm.doc.assignment_type=="External"){
            cur_frm.doc.workflow_state = "Approved By Director(X)"
        }

    },

    city: function(frm) {
    	if (cur_frm.doc.city=='Riyadh'){
    		cur_frm.set_value("external_per_diem_rate", 0);
            cur_frm.set_value("internal_per_diem_rate", 0);
    	}

    },
    
    onload: function(frm) {
    }
});

cur_frm.cscript.custom_assignment_type =
    cur_frm.cscript.custom_employee = function(doc, cdt, cd) {
        // get_grade_info(cur_frm);
        cur_frm.set_value("city", "");
        if (doc.assignment_type === 'Internal') {
            cur_frm.set_query("city", function() {
                return {
                    filters: [
                        ["City", "location", "=", "Internal"]
                    ]
                };
            });
        }
        if (doc.assignment_type === 'External') {
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
