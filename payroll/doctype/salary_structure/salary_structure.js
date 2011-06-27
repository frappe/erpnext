cur_frm.add_fetch('employee', 'company', 'company');

// On load
//=======================================================================
cur_frm.cscript.onload = function(doc, dt, dn){
  e_tbl = getchildren('Earning Detail', doc.name, 'earning_details', doc.doctype);
  d_tbl = getchildren('Deduction Detail', doc.name, 'deduction_details', doc.doctype);
  if (e_tbl.length == 0 && d_tbl.length == 0)
    $c_obj(make_doclist(doc.doctype,doc.name),'make_earn_ded_table','', function(r, rt) { refresh_many(['earning_details', 'deduction_details']);});
}

// On refresh
//=======================================================================
cur_frm.cscript.refresh = function(doc, dt, dn){
  if((!doc.__islocal) && (doc.is_active == 'Yes')){
    cur_frm.add_custom_button('Make IT Checklist', cur_frm.cscript['Make IT Checklist']);
    cur_frm.add_custom_button('Make Salary Slip', cur_frm.cscript['Make Salary Slip']);
  
    get_field(doc.doctype, 'employee', doc.name).permlevel = 1;
    refresh_field('employee');
  }
}

// Make IT checklist
//=======================================================================
cur_frm.cscript['Make IT Checklist']=function(){
  var itc = LocalDB.create('IT Checklist');
  itc = locals['IT Checklist'][itc];
  itc.employee = cur_frm.doc.employee;
  itc.fiscal_year = sys_defaults.fiscal_year;
  itc.is_cheklist_active='Yes';
  loaddoc('IT Checklist', itc.name);
}

// Make Salry Slip
//=======================================================================
cur_frm.cscript['Make Salary Slip'] = function(){
  var doc = cur_frm.doc;  
  var callback = function(r,rt){
    ret = r.message;
    n = createLocal("Salary Slip");
    $c('dt_map', args={
      'docs':compress_doclist([locals["Salary Slip"][n]]),
      'from_doctype':'Salary Structure',
      'to_doctype':'Salary Slip',
      'from_docname':doc.name,
      'from_to_list':"[['Salary Structure', 'Salary Slip'], ['Earning Detail', 'SS Earning Detail'], ['Deduction Detail', 'SS Deduction Detail']]"
      }, 
      function(r,rt) {
        n.fiscal_year = sys_defaults.fiscal_year;
        n.bank_name = ret['bank_name'];
        n.bank_account_no = ret['bank_ac_no'];
        n.esic_no=ret['esic_no'];
        n.pf_no= ret['pf_no'];
        loaddoc("Salary Slip", n);
      }
    );
  }
  $c_obj(make_doclist(doc.doctype,doc.name),'get_ss_values',cur_frm.doc.employee, callback); 
}


// get employee details
//=======================================================================
cur_frm.cscript.employee = function(doc, dt, dn){
  if (doc.employee)
    get_server_fields('get_employee_details','','',doc,dt,dn);
}

// calculate earning totals 
//=======================================================================
cur_frm.cscript.modified_value = function(doc, cdt, cdn){
  calculate_totals(doc, cdt, cdn);
}

// calculate deduction totals
//=======================================================================
cur_frm.cscript.d_modified_amt = function(doc, cdt, cdn){
  calculate_totals(doc, cdt, cdn);
}

// calculate totals
//=======================================================================
var calculate_totals = function(doc, cdt, cdn) {
  var tbl1 = getchildren('Earning Detail', doc.name, 'earning_details', doc.doctype);
  var tbl2 = getchildren('Deduction Detail', doc.name, 'deduction_details', doc.doctype);
  
  var total_earn = 0; var total_ded = 0;
  for(var i = 0; i < tbl1.length; i++){
    total_earn += flt(tbl1[i].modified_value);
  }
  for(var j = 0; j < tbl2.length; j++){
    total_ded += flt(tbl2[j].d_modified_amt);
  }
  doc.total_earning = total_earn;
  doc.total_deduction = total_ded;
  doc.net_pay = flt(total_earn) - flt(total_ded);
  refresh_many(['total_earning', 'total_deduction', 'net_pay']);
}

// validate
//=======================================================================
cur_frm.cscript.validate = function(doc, cdt, cdn) {
  calculate_totals(doc, cdt, cdn);
}
