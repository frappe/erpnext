// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

var bin_list = [];
var msg = [];
var binidx = 0;

cur_frm.cscript.repost_bin = function(doc,cdt,cdn) {
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
cur_frm.cscript.repost_account_balances = function(doc,cdt,cdn) {
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