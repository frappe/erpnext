// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc,cdt,cdn){
  if(doc.__islocal){
    var callback1 = function(r,rt){
      refresh_field('percentages');
    }

    return $c('runserverobj',args={'method':'get_months', 'docs':doc}, callback1);
  }
}

cur_frm.cscript.refresh = function(doc,cdt,cdn){
	cur_frm.toggle_display('distribution_id', doc.__islocal);
}
