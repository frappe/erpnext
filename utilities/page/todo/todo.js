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

wn.provide('erpnext.todo');

erpnext.todo.refresh = function() {
	wn.call({
		method: 'utilities.page.todo.todo.get',
		callback: function(r,rt) {
			var todo_list = $('#todo-list div.todo-content');
			var assigned_todo_list = $('#assigned-todo-list div.todo-content');
			todo_list.empty();
			assigned_todo_list.empty();
			
			var nothing_to_do = function() {
				$('#todo-list div.todo-content')
					.html('<div class="alert">Nothing to do :)</div>');
			}
			
			
			if(r.message) {
				for(var i in r.message) {
					new erpnext.todo.ToDoItem(r.message[i]);
				}
				if (!todo_list.html()) { nothing_to_do(); }
			} else {
				nothing_to_do();
			}
		}
	});
}

erpnext.todo.ToDoItem = Class.extend({
	init: function(todo) {
		label_map = {
			'High': 'label-important',
			'Medium': 'label-info',
			'Low':''
		}
		todo.labelclass = label_map[todo.priority];
		todo.userdate = dateutil.str_to_user(todo.date) || '';
		
		todo.fullname = '';
		if(todo.assigned_by) {
			var assigned_by = wn.boot.user_info[todo.assigned_by]
			todo.fullname = repl("[By %(fullname)s] ".bold(), {
				fullname: (assigned_by ? assigned_by.fullname : todo.assigned_by),
			});
		}
		
		var parent_list = "#todo-list";
		if(todo.owner !== user) {
			var owner = wn.boot.user_info[todo.owner];
			todo.fullname = repl("[To %(fullname)s] ".bold(), {
				fullname: (owner ? owner.fullname : todo.owner),
			});
		}
		parent_list += " div.todo-content";
		
		if(todo.reference_name && todo.reference_type) {
			todo.link = repl('<a href="#!Form/%(reference_type)s/%(reference_name)s">\
						%(reference_type)s: %(reference_name)s</a>', todo);
		} else if(todo.reference_type) {
			todo.link = repl('<br><a href="#!List/%(reference_type)s">\
						%(reference_type)s</a>', todo);
		} else {
			todo.link = '';
		}
		if(!todo.description) todo.description = '';
		todo.description_display = todo.description.replace(/\n\n/g, "<br>").trim();
				
		$(parent_list).append(repl('\
			<div class="todoitem">\
				<div class="label %(labelclass)s">%(priority)s</div>\
				<div class="popup-on-click"><a href="#">[edit]</a></div>\
				<div class="todo-date-fullname">\
					<div class="todo-date">%(userdate)s</div>\
					%(fullname)s:\
				</div>\
				<div class="description">%(description_display)s\
					<span class="ref_link">%(link)s</span>\
				</div>\
				<div class="close-span"><a href="#" class="close">&times;</a></div>\
			</div>\
			<div class="todo-separator"></div>', todo));
		$todo = $(parent_list + ' div.todoitem:last');
		
		if(todo.checked) {
			$todo.find('.description').css('text-decoration', 'line-through');
		}
		
		if(!todo.reference_type)
			$todo.find('.ref_link').toggle(false);
		
		$todo.find('.popup-on-click')
			.data('todo', todo)
			.click(function() {
				erpnext.todo.make_dialog($(this).data('todo'));
				return false;
			});
			
		$todo.find('.close')
			.data('name', todo.name)
			.click(function() {
				$(this).parent().css('opacity', 0.5);
				wn.call({
					method:'utilities.page.todo.todo.delete',
					args: {name: $(this).data('name')},
					callback: function() {
						erpnext.todo.refresh();
					}
				});
				return false;
			})
	}
});

erpnext.todo.make_dialog = function(det) {
	if(!erpnext.todo.dialog) {
		var dialog = new wn.ui.Dialog({
			width: 480,
			title: 'To Do', 
			fields: [
				{fieldtype:'Text', fieldname:'description', label:'Description', 
					reqd:1},
				{fieldtype:'Date', fieldname:'date', label:'Event Date', reqd:1},
				{fieldtype:'Check', fieldname:'checked', label:'Completed'},
				{fieldtype:'Select', fieldname:'priority', label:'Priority', reqd:1, 'options':['Medium','High','Low'].join('\n')},
				{fieldtype:'Button', fieldname:'save', label:'Save (Ctrl+S)'}
			]
		});
		
		dialog.fields_dict.save.input.onclick = function() {
			erpnext.todo.save(this);	
		}
		erpnext.todo.dialog = dialog;
	}

	if(det) {
		erpnext.todo.dialog.set_values({
			date: det.date,
			priority: det.priority,
			description: det.description,
			checked: det.checked
		});
		erpnext.todo.dialog.det = det;		
	}
	erpnext.todo.dialog.show();
	
}

erpnext.todo.save = function(btn) {
	var d = erpnext.todo.dialog;
	var det = d.get_values();
	
	if(!det) {
	 	return;
	}
	
	det.name = d.det.name || '';
	wn.call({
		method:'utilities.page.todo.todo.edit',
		args: det,
		btn: btn,
		callback: function() {
			erpnext.todo.dialog.hide();
			erpnext.todo.refresh();
		}
	});
}

wn.pages.todo.onload = function(wrapper) {
	// create app frame
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'), 'To Do');
	wrapper.appframe.add_home_breadcrumb();
	wrapper.appframe.add_breadcrumb(wn.modules["To Do"].icon);
	wrapper.appframe.add_button('Refresh', erpnext.todo.refresh, 'icon-refresh');
	wrapper.appframe.add_button('Add', function() {
		erpnext.todo.make_dialog({
			date:get_today(), priority:'Medium', checked:0, description:''});
	}, 'icon-plus');
	wrapper.appframe.add_ripped_paper_effect(wrapper);
	
	// show report button for System Manager
	if(wn.boot.profile.roles.indexOf("System Manager") !== -1) {
		wrapper.appframe.add_button("Report", function() { wn.set_route("query-report", "todo"); },
			"icon-table");
	}

	// load todos
	erpnext.todo.refresh();
	
	// save on click
	wrapper.save_action = function() {
		if(erpnext.todo.dialog && erpnext.todo.dialog.display) {
			erpnext.todo.dialog.fields_dict.save.input.click();
		}
	};
}