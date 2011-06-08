pscript['onload_Import Data'] = function() {
  
  //alert(profile.can_get_report);

  callback = function(r,rt) {
    var h = new PageHeader('di_header','Import Data','Tool to download template and upload data');
    var sel = $i('import_template');
    if(r.message){
      add_sel_options(sel, r.message);
      sel.onchange=function(){
        $i('child_tab_lst').innerHTML ='';
        if(sel.value != 'Select Master...'){
          $c_obj('Import Data Control','get_child_lst',sel.value,
            function(r,rt){
              var me = this;
              $y($i('child_tab_lst'),{backgroundColor:'#EEEEEE'})
              var desc = $a($i('child_tab_lst'), 'div', '', {padding:'8px'});
              
              desc.innerHTML = "<h4>Please click on following link(s) to download template.</h4>";
 
              
              var parent = $a($i('child_tab_lst'), 'div');
              var tab = make_table(parent,r.message.length,1,'100%',[],{padding:'8px',fontSize:'15px',borderCollapse: 'collapse'});
              
              for(var i=0;i<r.message.length;i++){
                var dt= $a($td(tab,i,0), 'span', 'link_type');
                dt.innerHTML = r.message[i];
                dt.nm = r.message[i];
                

                dt.onclick = function(){ 
					var ovr = $('input[name="overwrite"]:checked').length;
                    window.location = outUrl + '?cmd=get_template&dt=' + this.nm + (ovr ? '&overwrite=1' : '');
                }
              }
            }  
          );
        }
      }
    }
  }
  $c_obj('Import Data Control','get_master_lst','',callback);
  

}
