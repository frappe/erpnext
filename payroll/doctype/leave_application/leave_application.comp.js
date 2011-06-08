
cur_frm.cscript.onload=function(doc,dt,dn){if(!doc.posting_date)set_multiple(dt,dn,{posting_date:get_today()});}
cur_frm.add_fetch('employee','employee_name','employee_name');cur_frm.cscript.employee=function(doc,dt,dn){get_leave_balance(doc,dt,dn);}
cur_frm.cscript.fiscal_year=function(doc,dt,dn){get_leave_balance(doc,dt,dn);}
cur_frm.cscript.leave_type=function(doc,dt,dn){get_leave_balance(doc,dt,dn);}
cur_frm.cscript.half_day=function(doc,dt,dn){if(doc.from_date){set_multiple(dt,dn,{to_date:doc.from_date});calculate_total_days(doc,dt,dn);}}
cur_frm.cscript.from_date=function(doc,dt,dn){if(cint(doc.half_day)==1){set_multiple(dt,dn,{to_date:doc.from_date});}
calculate_total_days(doc,dt,dn);}
cur_frm.cscript.to_date=function(doc,dt,dn){if(cint(doc.half_day)==1&&doc.from_date&&doc.from_date!=doc.to_date){msgprint("To Date should be same as From Date for Half Day leave");return;}
if(cint(doc.half_day)==1){set_multiple(dt,dn,{to_date:doc.from_date});}
calculate_total_days(doc,dt,dn);}
get_leave_balance=function(doc,dt,dn){if(doc.employee&&doc.leave_type&&doc.fiscal_year)
get_server_fields('get_leave_balance','','',doc,dt,dn,1);}
calculate_total_days=function(doc,dt,dn){if(doc.from_date&&doc.to_date){if(cint(doc.half_day)==1)set_multiple(dt,dn,{total_leave_days:0.5});else{get_server_fields('get_total_leave_days','','',doc,dt,dn,1);}}}