cur_frm.cscript.is_list = function(d) { return d.modules_or_list=='List' ? 1 : 0 }
cur_frm.cscript.is_modules = function(d) { return d.modules_or_list=='Modules' ? 1 : 0 }

cur_frm.cscript['Do Transfer'] = function(doc) {
  al = getchildren('Transfer Account', doc.name, 'transfer_accounts');
  ml = getchildren('Transfer Module', doc.name, 'transfer_modules');
  sl = doc.selected_list.split(NEWLINE)
  
  cur_frm.cscript.cancel_transfer = 0;

  cur_frm.cscript.do_list = [];

  // for each account
  for(var ai = 0; ai < al.length; ai++) {


    // if transfer
    if(cint(al[ai].transfer)) {

      // module
      // ------
      if(doc.modules_or_list == 'Modules') {
      
        for(var mi = 0; mi < ml.length; mi++) {
        
          if(ml[mi].transfer) {
            var args = {server:al[ai].server, path:al[ai].path, pwd:al[ai].admin_password, act: al[ai].account, module:ml[mi].module, transfer_what:doc.transfer_what}
            cur_frm.cscript.do_list.push(args);
          }
        }
      }

      // list
      // ------
      if(doc.modules_or_list == 'List') {
      
        for(var si = 0; si < sl.length; si++) {
          if(sl[si]){
          var s = sl[si].split(',');        
          var args = {server:al[ai].server, path:al[ai].path, pwd:al[ai].admin_password, act: al[ai].account, dt: strip(s[0]), dn:strip(s[1]), transfer_what:doc.transfer_what}
          cur_frm.cscript.do_list.push(args);}
        }
      }
    }

  }
  
  locals[doc.doctype][doc.name].transfer_log = 'Transferring...'.bold();
  refresh_field('transfer_log');
    
  if(cur_frm.cscript.do_list.length)
  	cur_frm.cscript.do_next();

}

cur_frm.cscript.do_next = function() {

  if(cur_frm.cscript.do_list.length){
    var t = cur_frm.cscript.do_list[0];

    // do transfer

    locals[doc.doctype][doc.name].transfer_log += '<br>Transferring... Account:' + t.act + ':' + t.module + ', Record:'+t.dt + ',' + t.dn;
    refresh_field('transfer_log');

    $c_obj(make_doclist(doc.doctype, doc.name), 'do_transfer', docstring(t), cur_frm.cscript.ret_fn);

    
    // remove from list
    var tmp = [];
    for(var i=1;i<cur_frm.cscript.do_list.length;i++)tmp.push(cur_frm.cscript.do_list[i]);
    cur_frm.cscript.do_list = tmp;
  }
}

cur_frm.cscript.ret_fn = function(r,rt) {
  locals[doc.doctype][doc.name].transfer_log += '<br>' + r.message;
  refresh_field('transfer_log');

  
  if(cur_frm.cscript.do_list.length <= 0) {
    locals[doc.doctype][doc.name].transfer_log += '<br><b>Completed!</b>';
    refresh_field('transfer_log');
    return;
  }
  if(!cur_frm.cscript.cancel_transfer)
    cur_frm.cscript.do_next();
  else {
    locals[doc.doctype][doc.name].transfer_log += '<br><b>Cancelled!</b>';
    refresh_field('transfer_log');

  }
}

cur_frm.cscript['Cancel Transfer'] = function(doc,dt,dn) {
  cur_frm.cscript.cancel_transfer = 1;
}


/*-------------------------- running remote script in account selected-----------------------*/

cur_frm.cscript['Update Accounts'] = function(doc) {
  var al = getchildren('Transfer Account', doc.name, 'transfer_accounts');
  
  cur_frm.cscript.update_list = [];
  cur_frm.cscript.cancel_updates = 0;
  
  for(var ai = 0; ai < al.length; ai++) {
    if(cint(al[ai].transfer)){
      var args = {server:al[ai].server, path:al[ai].path, pwd:al[ai].admin_password, act: al[ai].account};
      cur_frm.cscript.update_list.push(args);
    }  
  }
  
  locals[doc.doctype][doc.name].transfer_log = 'Updating...'.bold();
  refresh_field('transfer_log');
    
  if(cur_frm.cscript.update_list.length)
    cur_frm.cscript.update_accounts();
}

cur_frm.cscript.update_accounts = function(){
  if(cur_frm.cscript.update_list.length){
    var t = cur_frm.cscript.update_list[0];

    // update account
    locals[doc.doctype][doc.name].transfer_log += '<br>Updating... Account:' + t.act;
    refresh_field('transfer_log');
    
    $c_obj(make_doclist(doc.doctype, doc.name), 'execute_remote_code', docstring(t), cur_frm.cscript.accounts_updated);
    
    // remove from list
    var tmp = [];
    for(var i=1;i<cur_frm.cscript.update_list.length;i++)tmp.push(cur_frm.cscript.update_list[i]);
    cur_frm.cscript.update_list = tmp;
  }
}

cur_frm.cscript.accounts_updated = function(r,rt){
  locals[doc.doctype][doc.name].transfer_log += '<br>' + r.message;
  refresh_field('transfer_log');

  if(cur_frm.cscript.update_list.length <= 0) {
    locals[doc.doctype][doc.name].transfer_log += '<br><b>Completed!</b>';
    refresh_field('transfer_log');
    return;
  }
  if(!cur_frm.cscript.cancel_updates)
    cur_frm.cscript.update_accounts();
  else {
    locals[doc.doctype][doc.name].transfer_log += '<br><b>Cancelled!</b>';
    refresh_field('transfer_log');
  }
}

cur_frm.cscript['Cancel Updates'] = function(doc,dt,dn) {
  cur_frm.cscript.cancel_updates = 1;
}