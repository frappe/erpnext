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

pscript['onload_Import Data'] = function() {
	
	//alert(profile.can_get_report);

	callback = function(r,rt) {
		var h = new PageHeader('di_header','Import Data','Tool to download template and upload data');
		var sel = $i('import_template');
		if(r.message){
			add_sel_options(sel, r.message);

			// please collapse here when editing :)
			sel.onchange=function(){
				$i('child_tab_lst').innerHTML ='';
				if(sel.value != 'Select Master...'){
					$c_obj('Import Data Control','get_child_lst',sel.value,
						function(r,rt){
							var me = this;
							$y($i('child_tab_lst'),{backgroundColor:'#EEEEEE', margin: '17px 17px', padding: '13px'})
							var desc = $a($i('child_tab_lst'), 'div', '', {padding:'4px'});
							
							desc.innerHTML = "<b>Download template(s) for importing "+sel_val(sel)+"</b>";
 
							
							var parent = $a($i('child_tab_lst'), 'div');
							var tab = make_table(parent,r.message.length,1,'100%',[],{padding:'3px',borderCollapse: 'collapse'});
							
							for(var i=0;i<r.message.length;i++){
								var dt= $a($td(tab,i,0), 'span', 'link_type');
								dt.innerHTML = r.message[i];
								dt.nm = r.message[i];
								
								dt.onclick = function(){ 
									var ovr = $('input[name="overwrite"]:checked').length;
										window.location = webnotes.request.url + '?cmd=get_template&dt=' + this.nm + (ovr ? '&overwrite=1' : '');
								}
							}
						}	
					);
				}
			}
		}
	
		// set the default (if given in url)
		if(window.location.hash) {
			var to_set = window.location.hash.split('/').slice(-1)[0];
			if(in_list(r.message, to_set)) {
				sel.value = to_set;
				sel.onchange();
			}
		}
	}
	$c_obj('Import Data Control','get_master_lst','',callback);
	

}
