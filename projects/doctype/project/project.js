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

// show tasks
wn.require("public/app/js/gantt_task.js");

cur_frm.cscript.refresh = function(doc) {
	if(!doc.__islocal) {
		// refresh gantt chart
		wn.require('app/projects/gantt_task.js');
		if(!cur_frm.gantt_area)
			cur_frm.gantt_area = $('<div>')
				.appendTo(cur_frm.fields_dict.project_tasks.wrapper);
		cur_frm.gantt_area.empty();
		erpnext.show_task_gantt(cur_frm.gantt_area, cur_frm.docname);		
	} else {
		if(cur_frm.gantt_area)
			cur_frm.gantt_area.empty();
	}
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;