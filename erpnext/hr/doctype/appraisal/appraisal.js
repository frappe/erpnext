// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
cur_frm.add_fetch('employee', 'department', 'department');

frappe.ui.form.on('Appraisal', {
    refresh: function(frm) {
    	if(!frm.doc.__islocal){
			frm.disable_save();
		}else{
			frm.enable_save();
		}
    },
    workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
        // if (cur_frm.doc.handled_by=="HR Specialist" && cur_frm.doc.other_expense>=1000){
        //     cur_frm.doc.workflow_state = "Approve By HR Specialist"
        //     }

    }
    
});

cur_frm.cscript.onload = function(doc,cdt,cdn){
	if(!doc.status)
		set_multiple(cdt,cdn,{status:'Draft'});
	if(doc.amended_from && doc.__islocal) {
		doc.status = "Draft";
	}
}

cur_frm.cscript.onload_post_render = function(doc,cdt,cdn){
	if(doc.__islocal && doc.employee==frappe.defaults.get_user_default("Employee")) {
		cur_frm.set_value("employee", "");
		cur_frm.set_value("employee_name", "")
	}
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){

}

cur_frm.cscript.kra_template = function(doc, dt, dn) {
	cur_frm.clear_table("goals");
	cur_frm.clear_table("quality_of_work_goals");
	cur_frm.clear_table("work_habits_goals");
	cur_frm.clear_table("job_knowledge_goals");
	cur_frm.clear_table("interpersonal_relations_goals");
	cur_frm.clear_table("leadership_goals");

	cur_frm.refresh_fields();
	erpnext.utils.map_current_doc({
		method: "erpnext.hr.doctype.appraisal.appraisal.fetch_appraisal_template",
		source_name: cur_frm.doc.kra_template,
		frm: cur_frm
	});
	
}

cur_frm.cscript.calculate_total_score = function(doc,cdt,cdn){
	//return get_server_fields('calculate_total','','',doc,cdt,cdn,1);
	var val = doc.goals || [];
	var total =0;
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned)
	}

	var val = doc.quality_of_work_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.work_habits_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.job_knowledge_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.interpersonal_relations_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.leadership_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	doc.total_score = flt(total)
	refresh_field('total_score')

	if (cur_frm.doc.total_score >= 95 && cur_frm.doc.total_score <= 100 ){
    		cur_frm.set_value("attribute", "Outstanding");
    	}else if (cur_frm.doc.total_score >= 90 && cur_frm.doc.total_score <= 94){
    		cur_frm.set_value("attribute", "Exceeds Requirements");
    	}else if (cur_frm.doc.total_score >= 80 && cur_frm.doc.total_score <= 89){
    		cur_frm.set_value("attribute", "Meets Requirements");
    	}else if (cur_frm.doc.total_score >= 70 && cur_frm.doc.total_score <= 79){
    		cur_frm.set_value("attribute", "Need Improvement");
    	}else if(cur_frm.doc.total_score >= 0 && cur_frm.doc.total_score <= 69){
    		cur_frm.set_value("attribute", "Unsatisfactory");
    }

}

cur_frm.cscript.score = function(doc,cdt,cdn){
	var d = locals[cdt][cdn];
	if (d.score){
		if (flt(d.score) > flt(d.per_weightage)) {
			msgprint(__("Score must be less than or equal to "+flt(d.per_weightage)));
			d.score = 0;
			refresh_field('score', d.name, 'goals');
			refresh_field('score', d.name, 'quality_of_work_goals');
			refresh_field('score', d.name, 'work_habits_goals');
			refresh_field('score', d.name, 'job_knowledge_goals');
			refresh_field('score', d.name, 'interpersonal_relations_goals');
			refresh_field('score', d.name, 'leadership_goals');
		}
		total = flt(d.score);
		// total = flt(d.per_weightage*d.score*2)/100;
		d.score_earned = total.toPrecision(2);
		refresh_field('score_earned', d.name, 'goals');
		refresh_field('score_earned', d.name, 'quality_of_work_goals');
		refresh_field('score_earned', d.name, 'work_habits_goals');
		refresh_field('score_earned', d.name, 'job_knowledge_goals');
		refresh_field('score_earned', d.name, 'interpersonal_relations_goals');
		refresh_field('score_earned', d.name, 'leadership_goals');
	}
	else{
		d.score_earned = 0;
		refresh_field('score_earned', d.name, 'goals');
		refresh_field('score_earned', d.name, 'quality_of_work_goals');
		refresh_field('score_earned', d.name, 'work_habits_goals');
		refresh_field('score_earned', d.name, 'job_knowledge_goals');
		refresh_field('score_earned', d.name, 'interpersonal_relations_goals');
		refresh_field('score_earned', d.name, 'leadership_goals');
	}
	cur_frm.cscript.calculate_total(doc,cdt,cdn);
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
	var val = doc.goals || [];
	var total =0;
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.quality_of_work_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.work_habits_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.job_knowledge_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.interpersonal_relations_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}

	var val = doc.leadership_goals || [];
	for(var i = 0; i<val.length; i++){
		total = flt(total)+flt(val[i].score_earned);
	}


	doc.total_score = flt(total);
	refresh_field('total_score');

	if (cur_frm.doc.total_score >= 95 && cur_frm.doc.total_score <= 100 ){
    		cur_frm.set_value("attribute", "Outstanding");
    	}else if (cur_frm.doc.total_score >= 90 && cur_frm.doc.total_score <= 94){
    		cur_frm.set_value("attribute", "Exceeds Requirements");
    	}else if (cur_frm.doc.total_score >= 80 && cur_frm.doc.total_score <= 89){
    		cur_frm.set_value("attribute", "Meets Requirements");
    	}else if (cur_frm.doc.total_score >= 70 && cur_frm.doc.total_score <= 79){
    		cur_frm.set_value("attribute", "Need Improvement");
    	}else if(cur_frm.doc.total_score >= 0 && cur_frm.doc.total_score <= 69){
    		cur_frm.set_value("attribute", "Unsatisfactory");
    }

}

cur_frm.fields_dict.employee.get_query = function(doc,cdt,cdn) {

	return{	query: "erpnext.controllers.queries.employee_query" }
}

