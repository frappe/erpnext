// ****************************************** onload ********************************************************
cur_frm.cscript.onload = function(doc, dt, dn) {
  if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
}


// ************************************** client triggers ***************************************************
// ---------
// employee
// ---------
cur_frm.add_fetch('employee','employee_name','employee_name');

cur_frm.cscript.employee = function (doc, dt, dn){
  get_leave_balance(doc, dt, dn);
}

// ------------
// fiscal_year
// ------------
cur_frm.cscript.fiscal_year = function (doc, dt, dn){
  get_leave_balance(doc, dt, dn);
}

// -----------
// leave type
// -----------
cur_frm.cscript.leave_type = function (doc, dt, dn){
  get_leave_balance(doc, dt, dn);
}

// ---------
// half day
// ---------
cur_frm.cscript.half_day = function(doc, dt, dn) {
  if(doc.from_date) {
    set_multiple(dt,dn,{to_date:doc.from_date});
    calculate_total_days(doc, dt, dn);
  }
}

// ---------
// from date
// ---------
cur_frm.cscript.from_date = function(doc, dt, dn) {
  if(cint(doc.half_day) == 1){
    set_multiple(dt,dn,{to_date:doc.from_date});
  }
  calculate_total_days(doc, dt, dn);
}

// --------
// to date
// --------
cur_frm.cscript.to_date = function(doc, dt, dn) {
  if(cint(doc.half_day) == 1 && cstr(doc.from_date) && doc.from_date != doc.to_date){
    msgprint("To Date should be same as From Date for Half Day leave");
    set_multiple(dt,dn,{to_date:doc.from_date});    
  }
  calculate_total_days(doc, dt, dn);
}


// ******************************************* utilities ****************************************************

// ------------------
// get leave balance
// ------------------
get_leave_balance = function(doc, dt, dn) {
  if(doc.employee && doc.leave_type && doc.fiscal_year)
    get_server_fields('get_leave_balance', '','', doc, dt, dn, 1);
}

// ---------------
// calculate days
// ---------------
calculate_total_days = function(doc, dt, dn) {
  if(doc.from_date && doc.to_date){
    if(cint(doc.half_day) == 1) set_multiple(dt,dn,{total_leave_days:0.5});
    else{
      //d = new DateFn();
      //set_multiple(dt,dn,{total_leave_days:d.get_diff(d.str_to_obj(doc.to_date),d.str_to_obj(doc.from_date))+1});
      get_server_fields('get_total_leave_days', '', '', doc, dt, dn, 1);
    }
  }
}
