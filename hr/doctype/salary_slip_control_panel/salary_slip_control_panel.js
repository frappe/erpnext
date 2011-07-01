cur_frm.cscript.onload = function(doc, cdt, cdn) {
  alert("Salary Slip Control Panel is currently under re-development. It will take around a week time.");
  hide_field(['Process Payroll', 'Submit Salary Slip', 'Make Bank Voucher']);
}

cur_frm.cscript['Process Payroll'] = function(doc,cdt,cdn){
  $c('runserverobj', args={'method':'process_payroll','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},function(r,rt){
    
      if(!pscript.ss_html)
        pscript.ss_html = $a(cur_frm.fields_dict['Salary Slip HTML'].wrapper,'span','',{border:'1px solid #CCC', backgroundColor:'#DDD'});
      pscript.ss_html.innerHTML = '';
      pscript.ss_html.innerHTML = r.message;
      
    
    });

}

cur_frm.cscript['Submit Salary Slip'] = function(doc,cdt,cdn){
  if(doc.month && doc.fiscal_year && doc.year){
    var check = confirm("DO you really want to Submit all Salary Slip for month : " + doc.month+" and year : "+doc.year);
    if(check){
      $c('runserverobj', args={'method':'submit_sal_slip','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},function(r,rt){
      
        if(!pscript.ss_html)
          pscript.ss_html = $a(cur_frm.fields_dict['Salary Slip HTML'].wrapper,'span','',{border:'1px solid #CCC', backgroundColor:'#DDD'});
        pscript.ss_html.innerHTML = '';
        pscript.ss_html.innerHTML = r.message;
        
      
      });
    }
  }
  else
    alert("Please select month, fiscal year and year");
}

// Make JV
// --------
cur_frm.cscript.make_jv = function(doc, dt, dn) {
  var call_back = function(r,rt){
    var jv = LocalDB.create('Journal Voucher');
    jv = locals['Journal Voucher'][jv];
    jv.voucher_type = 'Bank Voucher';
    jv.remark = 'Salary - Bank Voucher';
    jv.fiscal_year = doc.fiscal_year;
    jv.company = doc.company;
    
    // credit to bank
    var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
    d1.account = r.message['default_bank_account'];

    // debit to salary account
    var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
    d1.account = r.message['default_salary_account'];
    if(!r.message['default_salary_account'] && !r.message['default_bank_account']) alert("To debit salary amount in salary head and credit amount from bank, you need to specify default salary account and default bank account in Global Defaults.\nGo to Setup, click on Company. Select a company.\nSelect Default Salary Account, Default Bank Account from Accounting tab.");
    else if(!r.message['default_salary_account']) alert("To debit salary amount you need to specify default salary account in Global Defaults.\nGo to Setup, click on Company. Select a company.\nSelect Default Salary Account from Accounting tab.");
    else if(!r.message['default_bank_account']) alert("To credit salary amount you need to specify default bank account in Global Defaults.\nGo to Setup, click on Company. Select a company.\nSelect Default Bank Account from Accounting tab.");
    loaddoc('Journal Voucher', jv.name);
  }
  $c_obj(make_doclist(dt,dn),'get_acct_dtl','',call_back);

}



// Make Journal Voucher
// --------------------
cur_frm.cscript['Make Bank Voucher'] = function(doc, dt, dn) {
  cur_frm.cscript.make_jv(doc,dt,dn);
}
