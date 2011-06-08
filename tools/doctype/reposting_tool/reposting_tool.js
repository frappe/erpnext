var bin_list = [];
var msg = [];
var binidx = 0;

cur_frm.cscript['Repost Bin'] = function(doc,cdt,cdn) {
  args = {'check': 'Bin'};
  $c_obj('Reposting Tool','get_count_for_reposting', docstring(args), function(r,rt) {
       bin_list = r.message;
       repair_bin();
    });
} 

function repair_single_bin(){
  $c_obj('Reposting Tool', 'repair_bin', cstr(bin_list[binidx]), function(r,rt) {
       for(i = 0; i < r.message.length ; i++){
         msg.push(r.message[i]);
       }
       repair_bin();
    });
}

function repair_bin(){
   if(binidx >= 10) {
       args = {'msg': msg, 'subject': 'Item Quantity'};
       $c_obj('Reposting Tool', 'send_mail', docstring(args));
       alert('Completed');
       return;
  }
  repair_single_bin();
  binidx ++;
}

// Batch for Account Balances
//======================================================
var acc_list = [];
var accidx = 0;
cur_frm.cscript['Repost Account Balances'] = function(doc,cdt,cdn) {
  args = {'check': 'Account Balance'};
  $c_obj('Reposting Tool','get_count_for_reposting', docstring(args), function(r,rt) {
       acc_list = r.message;
       repair_acc_bal();
    });
} 

function repair_single_acc_bal(){
  $c_obj('Reposting Tool', 'repair_acc_bal', cstr(acc_list[accidx]), function(r,rt) {
       for(i = 0; i < r.message.length; i++){
         msg.push(r.message[i]);
       }
       repair_acc_bal();
    });
}

function repair_acc_bal(){
  if(accidx >= 15) {
     args = {'msg' : msg, 'subject': 'Account Balance'};
     $c_obj('Reposting Tool', 'send_mail', docstring(args));
     alert('Completed');
     return;
  }
  repair_single_acc_bal();
  accidx ++;
}