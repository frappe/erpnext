wn.provide('erpnext.todo');

erpnext.todo.refresh = function() {
	wn.call({
		method: 'utilities.page.todo.todo.get',
		callback: function(r,rt) {
			$('#todo-list').empty();
			if(r.message) {
				for(var i in r.message) {
					new erpnext.todo.ToDoItem(r.message[i]);
				}
			} else {
				$('#todo-list').html('<div class="help-box">Nothing to do :)</div>');
			}
		}
	});
	
	$('#add-todo').click(function() {
		erpnext.todo.make_dialog({
			date:get_today(), priority:'Medium', checked:0, description:''});
	})
}

erpnext.todo.ToDoItem = Class.extend({
	init: function(todo) {
		label_map = {
			'High': 'label-important',
			'Medium': 'label-info',
			'Low':''
		}
		todo.labelclass = label_map[todo.priority];
		todo.userdate = dateutil.str_to_user(todo.date);
		$('#todo-list').append(repl('<div class="todoitem">\
				<span class="description">\
					<span class="label %(labelclass)s">%(priority)s</span>\
					<span class="help" style="margin-right: 7px">%(userdate)s</span>\
					%(description)s</span>\
					<span class="ref_link">&rarr;\
					<a href="#!Form/%(reference_type)s/%(reference_name)s">\
						[%(reference_name)s]</a></span>\
					<a href="#" class="close">&times;</a>\
		</div>', todo));
		$todo = $('div.todoitem:last');
		
		if(todo.checked) {
			$todo.find('.description').css('text-decoration', 'line-through');
		}
		
		if(!todo.reference_name)
			$todo.find('.ref_link').toggle(false);
		
		$todo.find('.description')
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
		var dialog = new wn.widgets.Dialog();
		dialog.make({
			width: 480,
			title: 'To Do', 
			fields: [
				{fieldtype:'Date', fieldname:'date', label:'Event Date', reqd:1},
				{fieldtype:'Text', fieldname:'description', label:'Description', reqd:1},
				{fieldtype:'Check', fieldname:'checked', label:'Completed'},
				{fieldtype:'Select', fieldname:'priority', label:'Priority', reqd:1, 'options':['Medium','High','Low'].join('\n')},
				{fieldtype:'Button', fieldname:'save', label:'Save'}
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

pscript.onload_todo = function() {
	// load todos
	erpnext.todo.refresh();
}