// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Grade', {
    refresh:function(frm) {
        frm.dashboard.heatmap_area.hide();
        frm.dashboard.links_area.hide();

        if (frm.doc.__islocal) {
            cur_frm.clear_table("employee_travel_expense_limit_table");
        //in employee_travel_expense_limit_table table in city_type set static value
            let row = frm.add_child('employee_travel_expense_limit_table', {
                city_type:"Metro City",
            });
            let row1= frm.add_child('employee_travel_expense_limit_table', {
                city_type:"Urban City",
            });
            let row2= frm.add_child('employee_travel_expense_limit_table', {
                city_type:"Other City",
            });
            frm.refresh_field('employee_travel_expense_limit_table');
        }
    },
})


frappe.ui.form.on('Employee Travel Expense Limit Table', {
   hotel:function(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'total',row.hotel + row.food +row.other);
    refresh_field('total');
   },
   food: function(_frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'total',row.hotel + row.food +row.other);
    refresh_field('total');
   }, 
   other: function(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'total',row.hotel + row.food +row.other);
    refresh_field('total');
   }, 
})


