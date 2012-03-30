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

pscript.onload_Webforms = function(){

  $c_obj('Home Control','get_acc_id','', function(r,rt) {
    if(r.message) {
      var acc_id = r.message; 
  var parent = $i('webform_div');
  new PageHeader(parent,'Web Forms','');
      
      var lead_dv = $a('lead_div','div', '', {border:'1px solid #AAA', padding:'8px', width:'90%'});
      var cust_issue_dv = $a('cust_issue_div','div', '', {border:'1px solid #AAA', padding:'8px', width:'95%'});
      var job_dv = $a('job_div','div', '', {border:'1px solid #AAA', padding:'8px', width:'95%'});
      var ticket_dv = $a('ticket_div','div', '', {border:'1px solid #AAA', padding:'8px', width:'95%'});

      // url
      if(window.location.href.indexOf('?')!=-1)
        var url = window.location.href.split('?')[0];
      else
        var url = window.location.href.split('#')[0];

      lead_dv.innerHTML = '&lt;iframe src ="'+url+'?ac_name='+acc_id+'&embed=Lead" width ="400" height="800" frameborder="0"&gt;&lt;/iframe&gt;';
      cust_issue_dv.innerHTML = '&lt;iframe src ="'+url+'?ac_name='+acc_id+'&embed=Customer Issue" width ="400" height="500" frameborder="0"&gt;&lt;/iframe&gt;';
      job_dv.innerHTML = '&lt;iframe src ="'+url+'?ac_name='+acc_id+'&embed=Job Application"  width ="400" height="800" frameborder="0""&gt;&lt;/iframe&gt;';
      ticket_dv.innerHTML = '&lt;iframe src ="'+url+'?ac_name='+acc_id+'&embed=Support Ticket"  width ="400" height="800" frameborder="0""&gt;&lt;/iframe&gt;';
    }
  }); 
}
