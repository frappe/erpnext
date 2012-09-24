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

pscript['onload_WIP Monitor'] = function(){
	wip = new WIP_Monitor();

	var h = new PageHeader('wip_head','Work in Progress Monitor','A quick glance at your work in progress and pipeline');
	h.add_button('Refresh', function(){ wip = new WIP_Monitor();}, 1, 'ui-icon-refresh');
	
}

// Work In Progress Monitor
// =========================================================================================================================================================
WIP_Monitor = function(){					
	var me = this;
  this.row_index = 0;
  $c_obj('Home Control','get_wip_counts','',function(r,rt){
    me.make_wip_dashboard(r.message);
  });
}


// Make wip dashboard
// ------------------
WIP_Monitor.prototype.make_wip_dashboard = function(wip_dict)
{
	var me = this;
	// list of doctypes which user can read
	var can_read_dt = ['Lead', 'Opportunity', 'Sales Order', 'Sales Invoice', 'Purchase Request', 'Purchase Order', 'Purchase Invoice', 'Delivery Note', 'Task', 'Serial No'];
  
	$i('wip_body').innerHTML = '';
	this.tab = make_table('wip_body',1,0,'100%',[],{padding:'4px'});

	for(var k=0; k<can_read_dt.length; k++){
	
    // check if the user can read these doctypes
		if(in_list(profile.can_read, get_doctype_label(can_read_dt[k])))
    {
      var work = can_read_dt[k];
      if(this.tab.rows[this.row_index].cells.length==2){
        this.row_index = this.row_index + 1;
        this.tab.insertRow(this.tab.rows.length);
      }
      var parent = this.tab.rows[this.row_index].insertCell(this.tab.rows[this.row_index].cells.length);
      $y(parent, {paddingBottom:'16px', width:'50%', paddingLeft:'8px'})
      me.show_wip_dashboard(parent, work, wip_dict[work]);
    }
	}
}


// Show wip dashboard
// ------------------
WIP_Monitor.prototype.show_wip_dashboard = function(parent, head, report_dict)
{
	var me = this;
	var report_dt
  
	// dictionary for labels to be displayed
	var wip_lbl_map = {'Lead':'Lead', 'Opportunity':'Enquiries', 'Sales Order':'Sales Order', 'Sales Invoice':'Invoices', 'Purchase Request':'Purchase Request', 'Purchase Order':'Purchase Order', 'Purchase Invoice':'Bills', 'Delivery Note':'Delivery Note', 'Task':'Tasks', 'Serial No':'Maintenance'};

	// header
	var h = $a(parent,'h3');

  h.innerHTML = wip_lbl_map[head];
  report_dt = head;
    
	for(report in report_dict){
		me.make_report_body(parent, report, report_dict[report], report_dt);
	}
}


// Make wip report body
// --------------------
WIP_Monitor.prototype.make_report_body = function(parent, lbl, records, rep_dt)
{
	var me = this;

	dt_color = lbl=='Overdue' ? 'red' : 'black';
	var tab2 = make_table(parent,1,2, '70%', ['10%', '90%'], {padding:'4px'});
			
	// no of records
	var s1 = $a($td(tab2,0,0), 'span', '', {fontWeight:'bold', fontSize:'12px', color:dt_color});
	s1.innerHTML = records;

	// link to report
	var s1 = $a($td(tab2,0,1), 'span', 'link_type', {cursor:'pointer', color:'#DFH'});
	s1.dt = rep_dt;     s1.cn = rep_dt + '-' + lbl;     s1.innerHTML = lbl;
	s1.onclick = function() { loadreport(this.dt, this.cn); }
}
