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

pscript.onload_Projects = function(wrapper) {
	wn.ui.make_app_page({parent:wrapper, title:'Gantt Chart: All Tasks', single_column:true});
	if(!erpnext.show_task_gantt)
		wn.require('app/js/gantt_task.js');

	var gantt_area = $('<div>').appendTo($(wrapper).find('.layout-main'));
	erpnext.show_task_gantt(gantt_area);
}