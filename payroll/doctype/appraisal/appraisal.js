cur_frm.add_fetch('employee', 'company', 'company');

cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(!doc.status) set_multiple(dt,dn,{status:'Draft'});
  if(doc.employee) cur_frm.cscript.employee(doc,cdt,cdn);
  if(doc.amended_from && doc.__islocal) cur_frm.cscript.refresh_appraisal_details(doc, cdt, cdn);
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
  if(user == doc.kra_approver && doc.status == 'Submitted') unhide_field(['Update', 'Declare Completed', 'Calculate Total Score']);
  else hide_field(['Update', 'Declare Completed', 'Calculate Total Score']);
  
  if(!doc.docstatus) unhide_field('Fetch Template');
  else hide_field('Fetch Template');
}


cur_frm.cscript.refresh_appraisal_details = function(doc, cdt, cdn){
  var val = getchildren('Appraisal Detail', doc.name, 'appraisal_details', doc.doctype);
  for(var i = 0; i<val.length; i++){
    set_multiple('Appraisal Detail', val[i].name, {'target_achieved':'', 'score':'', 'scored_earned':''}, 'appraisal_details');
  }
  doc.total_score = '';
  refresh_field('appraisal_details');
  refresh_field('total_score');
}

cur_frm.cscript.employee = function(doc,cdt,cdn){
  if(doc.employee){
    $c_obj(make_doclist(doc.doctype, doc.name),'set_approver','', function(r,rt){
      if(r.message){
        doc.employee_name = r.message['emp_nm'];
        get_field(doc.doctype, 'kra_approver' , doc.name).options = r.message['app_lst'];        
        refresh_many(['kra_approver','employee_name']);
      }    
    });
  }
}

cur_frm.cscript['Calculate Total Score'] = function(doc,cdt,cdn){
  //get_server_fields('calculate_total','','',doc,cdt,cdn,1);
  var val = getchildren('Appraisal Detail', doc.name, 'appraisal_details', doc.doctype);
  var total =0;
  for(var i = 0; i<val.length; i++){
    total = flt(total)+flt(val[i].score_earned)
  }
  doc.total_score = flt(total)
  refresh_field('total_score')
}

/*cur_frm.cscript['Declare Completed'] = function(doc,cdt,cdn){
  $c_obj(make_doclist(doc.doctype, doc.name),'declare_completed','', function(r,rt){
    if(r.message){
      refresh_field('Status');
      cur_frm.cscript.refresh(doc,cdt,cdn);
    }
  });
}*/

cur_frm.cscript['Declare Completed'] = function(doc,cdt,cdn){
  var declare_completed_dialog;
  
  set_declare_completed_dialog = function() {
    declare_completed_dialog = new Dialog(400, 200, 'Declare Completed');
    declare_completed_dialog.make_body([
      ['HTML', 'Message', '<div class = "comment">You wont be able to do any changes after declaring this Appraisal as completed. Are you sure, you want to declare it as completed ?</div>'],
      ['HTML', 'Response', '<div class = "comment" id="declare_completed_dialog_response"></div>'],
      ['HTML', 'Declare Completed', '<div></div>']
    ]);
    
    var declare_completed_btn1 = $a($i(declare_completed_dialog.widgets['Declare Completed']), 'button', 'button');
    declare_completed_btn1.innerHTML = 'Yes';
    declare_completed_btn1.onclick = function(){ declare_completed_dialog.add(); }
    
    var declare_completed_btn2 = $a($i(declare_completed_dialog.widgets['Declare Completed']), 'button', 'button');
    declare_completed_btn2.innerHTML = 'No';
    $y(declare_completed_btn2,{marginLeft:'4px'});
    declare_completed_btn2.onclick = function(){ declare_completed_dialog.hide();}
    
    declare_completed_dialog.onshow = function() {
      $i('declare_completed_dialog_response').innerHTML = '';
    }
    
    declare_completed_dialog.refresh_dt = function(){
      cur_frm.cscript.refresh(this.doc, this.cdt, this.cdn);
      msgprint("refersh done");
      $c('webnotes.widgets.form.form_header.refresh_labels',this.doc,function(r,rt){});
    }
    
    declare_completed_dialog.add = function() {
      // sending...
      $i('declare_completed_dialog_response').innerHTML = 'Processing...';
      var m_arg = user+ '~~' + this.msg_nm_lst;
      
      $c_obj(make_doclist(this.doc.doctype, this.doc.name),'declare_completed','', function(r,rt){
        
        if(r.message.status == 'Completed'){
          $i('declare_completed_dialog_response').innerHTML = 'Done';
          refresh_field('status');
          declare_completed_dialog.refresh_dt();
          hide_field(['Update', 'Declare Completed', 'Calculate Total Score']);
          declare_completed_dialog.hide();
        }
        else if(r.message.status == 'Incomplete'){
          $i('declare_completed_dialog_response').innerHTML = 'Incomplete Appraisal';
        }
        else if(r.message.status == 'No Score'){
          $i('declare_completed_dialog_response').innerHTML = 'Calculate total score';
        }
      });
    }
  }  
  
  if(!declare_completed_dialog){
    set_declare_completed_dialog();
  }  
  declare_completed_dialog.doc = doc;
  declare_completed_dialog.cdt = cdt;
  declare_completed_dialog.cdn = cdn;
  declare_completed_dialog.show();
}

cur_frm.cscript.score = function(doc,cdt,cdn){
  var d = locals[cdt][cdn];
  if (d.score){
    total = flt(d.per_weightage*d.score)/100;
    d.score_earned = total.toPrecision(2);
    refresh_field('score_earned', d.name, 'appraisal_details');
  }
  else{
    d.score_earned = '';
    refresh_field('score_earned', d.name, 'appraisal_details');
  }
  cur_frm.cscript.calculate_total(doc,cdt,cdn);
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
  var val = getchildren('Appraisal Detail', doc.name, 'appraisal_details', doc.doctype);
  var total =0;
  for(var i = 0; i<val.length; i++){
    total = flt(total)+flt(val[i].score_earned);
  }
  doc.total_score = flt(total);
  refresh_field('total_score');
}
