// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('project','executive_summary','executive_summary');
frappe.ui.form.on('Project Status Report', {
    refresh: function (frm) {

    }
});


cur_frm.cscript.custom_report_type =
cur_frm.cscript.custom_project = function (doc, cdt, cd) {
    // debugger;
    if( ! doc.project ){
        return;
    }
    var task_args = {
        report_type: cur_frm.doc.report_type,
        start_date: cur_frm.doc.project_start_date
    }
    call('get_project_task_major', 'major_accomplishments', add_task_row, task_args);
    call('get_project_task_planned', 'planned_accomplishments', add_task_row, task_args);
    call('get_project_task_milestone', 'project_milestone_progress', add_task_row,  task_args);
    call('get_project_risk', 'project_risk', add_risk_row, {is_issue:0});
    call('get_project_risk', 'project_issues', add_risk_row, {is_issue:1});
};


function call(func_name, parentfield,callback, args) {
    cur_frm.clear_table(parentfield);

    args.name = cur_frm.doc.project
    console.lgo
    frappe.call({
        method: 'erpnext.projects.doctype.project.project.' + func_name,
        args: args,
        callback: function (r) {
            if (r.message) {
                $.each(r.message, function (i, d) {

                   callback(d, parentfield);
                });
                refresh_field(parentfield);
            }

        }
    });

}

function add_task_row(data, parentfield) {
    var row = frappe.model.add_child(cur_frm.doc, "Project Task", parentfield);
    row.title= data.subject;
    row.status= data.status;
    row.start_date= data.exp_start_date;
    row.end_date= data.exp_end_date;
    row.description= data.description;
    row.task_id= data.name;
    row.is_milestone= data.is_milestone;
}

function add_task_row_old(data, parentfield) {
    var row = frappe.model.add_child(cur_frm.doc, "Task", parentfield);
    row.subject = data.subject;
    row.project = data.project;
    row.status = data.status;
    row.priority = data.priority;
    row.exp_start_date = data.exp_start_date;
    row.expected_time = data.expected_time;
    row.exp_end_date = data.exp_end_date;
    row.description = data.description;
    row.depends_on = data.depends_on;
    row.actual = data.actual;
    row.act_start_date = data.act_start_date;
    row.actual_time = data.actual_time;
    row.progress = data.progress;
    row.act_end_date = data.act_end_date;
    row.total_costing_amount = data.total_costing_amount;
    row.total_expense_claim = data.total_expense_claim;
    row.total_billing_amount = data.total_billing_amount;
    row.more_details = data.more_details;
    row.review_date = data.review_date;
    row.closing_date = data.closing_date;
    row.company = data.company;
}


function add_risk_row(data, parentfield) {
    var row = frappe.model.add_child(cur_frm.doc, "Project Risk", parentfield);
    row.risk = data.risk;
    row.likelihood = data.likelihood;
    row.responsible = data.responsible;
    row.status = data.status;
    row.impact = data.impact;
    row.risk_mitigation = data.risk_mitigation;
    row.closing_date = data.closing_date;
}

function add_issues_row(data, parentfield) {
    var row = frappe.model.add_child(cur_frm.doc, "Project Risk", parentfield);
    row.risk = data.risk;
    row.likelihood = data.likelihood;
    row.responsible = data.responsible;
    row.status = data.status;
    row.impact = data.impact;
    row.risk_mitigation = data.risk_mitigation;
    row.closing_date = data.closing_date;
}
