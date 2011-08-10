cur_frm.add_fetch('employee', 'company', 'company');

// On load
// -------------------------------------------------------------------
cur_frm.cscript.onload = function(doc,dt,dn){
  if((cint(doc.__islocal) == 1) && !doc.amended_from){
    var today=new Date();
    month = (today.getMonth()+01).toString();
    if(month.length>1) doc.month = month;
    else doc.month = '0'+month;
		doc.fiscal_year = sys_defaults['fiscal_year'];
    refresh_many(['month', 'fiscal_year']);
    cur_frm.cscript.fiscal_year(doc, dt, dn);
  }
}

// Get leave details
//---------------------------------------------------------------------
cur_frm.cscript.fiscal_year = function(doc,dt,dn){
    $c_obj(make_doclist(doc.doctype,doc.name), 'get_emp_and_leave_details','',function(r, rt) {
      var doc = locals[dt][dn];
      cur_frm.refresh();
      calculate_all(doc, dt, dn);
    });
}

cur_frm.cscript.month = cur_frm.cscript.employee = cur_frm.cscript.fiscal_year;

// Calculate total if lwp exists
// ------------------------------------------------------------------------
cur_frm.cscript.leave_without_pay = function(doc,dt,dn){
  doc.payment_days = flt(doc.total_days_in_month) - flt(doc.leave_without_pay);
  refresh_field('payment_days');
  calculate_all(doc, dt, dn);
}

// Calculate all
// ------------------------------------------------------------------------
var calculate_all = function(doc, dt, dn) {
  calculate_earning_total(doc, dt, dn);
  calculate_ded_total(doc, dt, dn);
  calculate_net_pay(doc, dt, dn);
}

// Trigger on earning modified amount and depends on lwp
// ------------------------------------------------------------------------
cur_frm.cscript.e_modified_amount = function(doc,dt,dn){
  calculate_earning_total(doc, dt, dn);
  calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.e_depends_on_lwp = cur_frm.cscript.e_modified_amount;

// Trigger on earning modified amount and depends on lwp
// ------------------------------------------------------------------------
cur_frm.cscript.d_modified_amount = function(doc,dt,dn){
  calculate_ded_total(doc, dt, dn);
  calculate_net_pay(doc, dt, dn);
}

cur_frm.cscript.d_depends_on_lwp = cur_frm.cscript.d_modified_amount;

// Calculate earning total
// ------------------------------------------------------------------------
var calculate_earning_total = function(doc, dt, dn) {
  var tbl = getchildren('SS Earning Detail', doc.name, 'earning_details', doc.doctype);

  var total_earn = 0;
  for(var i = 0; i < tbl.length; i++){
    if(cint(tbl[i].e_depends_on_lwp) == 1) {
      tbl[i].e_modified_amount = flt(tbl[i].e_amount)*(flt(doc.payment_days)/cint(doc.total_days_in_month));      
      refresh_field('e_modified_amount', tbl[i].name, 'earning_details');
    }
    total_earn += flt(tbl[i].e_modified_amount);
  }
  doc.gross_pay = total_earn + flt(doc.arrear_amount) + flt(doc.leave_encashment_amount);
  refresh_many(['e_modified_amount', 'gross_pay']);
}

// Calculate deduction total
// ------------------------------------------------------------------------
var calculate_ded_total = function(doc, dt, dn) {
  var tbl = getchildren('SS Deduction Detail', doc.name, 'deduction_details', doc.doctype);

  var total_ded = 0;
  for(var i = 0; i < tbl.length; i++){
    if(cint(tbl[i].d_depends_on_lwp) == 1) {
      tbl[i].d_modified_amount = flt(tbl[i].d_amount)*(flt(doc.payment_days)/cint(doc.total_days_in_month));
			refresh_field('d_modified_amount', tbl[i].name, 'deduction_details');
    }
    total_ded += flt(tbl[i].d_modified_amount);
  }
  doc.total_deduction = total_ded;
  refresh_field('total_deduction');  
}

// Calculate net payable amount
// ------------------------------------------------------------------------
var calculate_net_pay = function(doc, dt, dn) {
  doc.net_pay = flt(doc.gross_pay) - flt(doc.total_deduction);
	doc.rounded_total = Math.round(doc.net_pay);
  refresh_many(['net_pay', 'rounded_total']);
}

// trigger on arrear
// ------------------------------------------------------------------------
cur_frm.cscript.arrear_amount = function(doc,dt,dn){
  calculate_earning_total(doc, dt, dn);
  calculate_net_pay(doc, dt, dn);
}

// trigger on encashed amount
// ------------------------------------------------------------------------
cur_frm.cscript.leave_encashment_amount = cur_frm.cscript.arrear_amount;

// validate
// ------------------------------------------------------------------------
cur_frm.cscript.validate = function(doc, dt, dn) {
  calculate_all(doc, dt, dn);
}
