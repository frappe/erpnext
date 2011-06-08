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
