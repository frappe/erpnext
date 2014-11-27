// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

 

//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
   frappe.call({
	   type:"GET",
	   method:"erpnext.manufacturing.doctype.workstation.workstation.get_default_holiday_list",
	   callback: function(r) {
		   if(!r.exe && r.message){
			   cur_frm.set_value("holiday_list", r.message);
		   }
	   }
   })
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}