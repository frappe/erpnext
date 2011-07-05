cur_frm.add_fetch('employee', 'company', 'company');

cur_frm.cscript.onload = function(doc,cdt,cdn){
  // 
  if(!doc.approval_status) set_multiple(cdt,cdn,{approval_status:'Draft'});
  if(doc.employee) cur_frm.cscript.employee(doc,cdt,cdn);
  
  if (doc.__islocal) {
    if(doc.amended_from) set_multiple(cdt,cdn,{approval_status:'Draft'});
    var val = getchildren('Expense Voucher Detail', doc.name, 'expense_voucher_details', doc.doctype);
    for(var i = 0; i<val.length; i++){
      val[i].sanctioned_amount ='';
    }
    //doc.total_claimed_amount = '';
    doc.total_sanctioned_amount = '';
    refresh_many(['sanctioned_amount', 'total_sanctioned_amount']);
  }
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
  if((user == doc.exp_approver && doc.approval_status == 'Submitted') || doc.docstatus == 0) unhide_field('Calculate Total Amount');
  else hide_field('Calculate Total Amount');
  
  if(user == doc.exp_approver && doc.approval_status == 'Submitted')  unhide_field(['Update Voucher', 'Approve', 'Reject']);

  else hide_field(['Update Voucher', 'Approve', 'Reject']);

  
  if(user == doc.exp_approver && doc.approval_status == 'Submitted') set_field_permlevel('remark', 0);
  else set_field_permlevel('remark', 1);
}

cur_frm.cscript.employee = function(doc,cdt,cdn){
  if(doc.employee){
    $c_obj(make_doclist(doc.doctype, doc.name),'set_approver','', function(r,rt){
      if(r.message){
        doc.employee_name = r.message['emp_nm'];
        get_field(doc.doctype, 'exp_approver' , doc.name).options = r.message['app_lst'];        
        refresh_many(['exp_approver','employee_name']);
      }    
    });
  }
}

cur_frm.cscript.calculate_total = function(doc,cdt,cdn){
  if(doc.approval_status == 'Draft'){
    var val = getchildren('Expense Voucher Detail', doc.name, 'expense_voucher_details', doc.doctype);
    var total_claim =0;
    for(var i = 0; i<val.length; i++){
      total_claim = flt(total_claim)+flt(val[i].claim_amount);
    }
    doc.total_claimed_amount = flt(total_claim);
    refresh_field('total_claimed_amount');
    
    $c_obj(make_doclist(doc.doctype, doc.name),'validate_approver','', function(r,rt){
      if(r.message){
        if(r.message['valid_approver'] == 'No'){
          doc.exp_approver ='';
        }
        get_field(doc.doctype, 'exp_approver' , doc.name).options = '';
        get_field(doc.doctype, 'exp_approver' , doc.name).options = r.message['app_lst'];
        refresh_field('exp_approver');
      }
    });
  }
  else if(doc.approval_status == 'Submitted'){
    var val = getchildren('Expense Voucher Detail', doc.name, 'expense_voucher_details', doc.doctype);
    var total_sanctioned = 0;
    for(var i = 0; i<val.length; i++){
      total_sanctioned = flt(total_sanctioned)+flt(val[i].sanctioned_amount);
    }
    doc.total_sanctioned_amount = flt(total_sanctioned);
    refresh_field('total_sanctioned_amount');
  }
}

cur_frm.cscript['Calculate Total Amount'] = function(doc,cdt,cdn){
  cur_frm.cscript.calculate_total(doc,cdt,cdn);
}
cur_frm.cscript.claim_amount = function(doc,cdt,cdn){
  cur_frm.cscript.calculate_total(doc,cdt,cdn);
}
cur_frm.cscript.sanctioned_amount = function(doc,cdt,cdn){
  cur_frm.cscript.calculate_total(doc,cdt,cdn);
}

cur_frm.cscript['Approve'] = function(doc,cdt,cdn){

  if(user == doc.exp_approver){
    var approve_voucher_dialog;
    
    set_approve_voucher_dialog = function() {
      approve_voucher_dialog = new Dialog(400, 200, 'Approve Voucher');
      approve_voucher_dialog.make_body([
        ['HTML', 'Message', '<div class = "comment">You wont be able to do any changes after approving this expense voucher. Are you sure, you want to approve it ?</div>'],
        ['HTML', 'Response', '<div class = "comment" id="approve_voucher_dialog_response"></div>'],
        ['HTML', 'Approve Voucher', '<div></div>']
      ]);
      
      var approve_voucher_btn1 = $a($i(approve_voucher_dialog.widgets['Approve Voucher']), 'button', 'button');
      approve_voucher_btn1.innerHTML = 'Yes';
      approve_voucher_btn1.onclick = function(){ approve_voucher_dialog.add(); }
      
      var approve_voucher_btn2 = $a($i(approve_voucher_dialog.widgets['Approve Voucher']), 'button', 'button');
      approve_voucher_btn2.innerHTML = 'No';
      $y(approve_voucher_btn2,{marginLeft:'4px'});
      approve_voucher_btn2.onclick = function(){ approve_voucher_dialog.hide();}
      
      approve_voucher_dialog.onshow = function() {
        $i('approve_voucher_dialog_response').innerHTML = '';
      }
      
      approve_voucher_dialog.add = function() {
        // sending...
        $i('approve_voucher_dialog_response').innerHTML = 'Processing...';
        
        $c_obj(make_doclist(this.doc.doctype, this.doc.name),'approve_voucher','', function(r,rt){
          if(r.message == 'Approved'){
            $i('approve_voucher_dialog_response').innerHTML = 'Approved';
            refresh_field('approval_status');
            hide_field(['Update Voucher', 'Approve', 'Reject', 'Calculate Total Amount']);
            approve_voucher_dialog.hide();
          }
          else if(r.message == 'Incomplete'){
            $i('approve_voucher_dialog_response').innerHTML = 'Incomplete Voucher';
          }
          else if(r.message == 'No Amount'){
            $i('approve_voucher_dialog_response').innerHTML = 'Calculate total amount';
          }
        });
      }
    }  
    
    if(!approve_voucher_dialog){
      set_approve_voucher_dialog();
    }  
    approve_voucher_dialog.doc = doc;
    approve_voucher_dialog.cdt = cdt;
    approve_voucher_dialog.cdn = cdn;
    approve_voucher_dialog.show();
    refresh_field('expense_voucher_details');
    doc.__unsaved = 0;
    cur_frm.refresh_header();
  }else{
    msgprint("Expense Voucher can be approved by Approver only");
  }
}

cur_frm.cscript['Reject'] = function(doc,cdt,cdn){
  if(user == doc.exp_approver){
    var reject_voucher_dialog;
    
    set_reject_voucher_dialog = function() {
      reject_voucher_dialog = new Dialog(400, 200, 'Reject Voucher');
      reject_voucher_dialog.make_body([
        ['HTML', 'Message', '<div class = "comment">You wont be able to do any changes after rejecting this expense voucher. Are you sure, you want to reject it ?</div>'],
        ['HTML', 'Response', '<div class = "comment" id="reject_voucher_dialog_response"></div>'],
        ['HTML', 'Reject Voucher', '<div></div>']
      ]);
      
      var reject_voucher_btn1 = $a($i(reject_voucher_dialog.widgets['Reject Voucher']), 'button', 'button');
      reject_voucher_btn1.innerHTML = 'Yes';
      reject_voucher_btn1.onclick = function(){ reject_voucher_dialog.add(); }
      
      var reject_voucher_btn2 = $a($i(reject_voucher_dialog.widgets['Reject Voucher']), 'button', 'button');
      reject_voucher_btn2.innerHTML = 'No';
      $y(reject_voucher_btn2,{marginLeft:'4px'});
      reject_voucher_btn2.onclick = function(){ reject_voucher_dialog.hide();}
      
      reject_voucher_dialog.onshow = function() {
        $i('reject_voucher_dialog_response').innerHTML = '';
      }
      
      reject_voucher_dialog.add = function() {
        // sending...
        $i('reject_voucher_dialog_response').innerHTML = 'Processing...';
        
        $c_obj(make_doclist(this.doc.doctype, this.doc.name),'reject_voucher','', function(r,rt){
          if(r.message == 'Rejected'){
            $i('reject_voucher_dialog_response').innerHTML = 'Rejected';
            refresh_field('approval_status');
            hide_field(['Update Voucher', 'Approve', 'Reject', 'Calculate Total Amount']);
            reject_voucher_dialog.hide();
          }
        });
      }
    }  
    
    if(!reject_voucher_dialog){
      set_reject_voucher_dialog();
    }  
    reject_voucher_dialog.doc = doc;
    reject_voucher_dialog.cdt = cdt;
    reject_voucher_dialog.cdn = cdn;
    reject_voucher_dialog.show();
    refresh_field('expense_voucher_details');
    doc.__unsaved = 0;
    cur_frm.refresh_header();
  }else{
    msgprint("Expense Voucher can be rejected by Approver only");
  }
}

//update follow up
//=================================================================================
cur_frm.cscript['Update Voucher'] = function(doc){

  $c_obj(make_doclist(doc.doctype, doc.name),'update_voucher','',function(r, rt){
    refresh_field('expense_voucher_details');
    doc.__unsaved = 0;
    cur_frm.refresh_header();
  });
}
