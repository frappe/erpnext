frappe.ready(function() {
	$( window ).load(function() {
		$(".btn-open-tasks").click();
		$(".btn-open-issues").click();
	});
	
	$('.btn-closed-tasks').click(function() {
		reload_items('closed','tasks');
	});	
	
	$('.btn-open-tasks').click(function() {
		reload_items('open','tasks');
	});

	$('.btn-closed-issues').click(function() {
		reload_items('closed','issues');
	});	
	
	$('.btn-open-issues').click(function() {
		reload_items('open','issues');
	});

	var start = 10;
	$(".more-tasks").click(function() {
		more_items('tasks', true);
	});	
	
	$(".more-issues").click(function() {
		more_items('issues', true);
	});	
	
	$(".more-timelogs").click(function() {
		more_items('timelogs', false);
	});	
	
	$(".more-timelines").click(function() {
		more_items('timelines', false);
	});	
	
	$( ".project-tasks" ).on('click', '.task-x', function() {
		var item_name = $(this).attr('id');
		close_item('task', item_name);
	});	
	
	$( ".project-issues" ).on('click', '.issue-x', function() {
		var item_name = $(this).attr('id');
		close_item('issue', item_name);
	});	
		
	var reload_items = function(item_status, item) {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_"+ item +"_html",
				project: '{{ doc.name }}',
				item_status: item_status,
			},
			dataType: "json",
			success: function(data) {
				$('.project-'+ item).html(data.message);
				
				$('.project-'+ item +'-section .btn-group .bold').removeClass('bold');
				$('.btn-'+ item_status +'-'+ item).addClass( "bold" );
				$(".more-"+ item).toggle(true);
			}
		});	
		
	}
	
	var more_items = function(item, item_status){
		if(item_status)
		{
			var item_status = $('.project-'+ item +'-section .btn-group .btn-primary').hasClass('btn-closed-'+ item) 
				? 'closed' : 'open';
		}
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_"+ item +"_html",
				project: '{{ doc.name }}',
				start: start,
				item_status: item_status,
			},
			dataType: "json",
			success: function(data) {
				$(data.message).appendTo('.project-'+ item);
				if(typeof data.message == 'undefined') {	
					$(".more-"+ item).toggle(false);	
				}
			start = start+10;
			}
		});				
	}
	
	var close_item = function(item, item_name){
		var args = {
			project: '{{ doc.name }}',
			item_name: item_name,
		}		
		frappe.call({
			btn: this,
			type: "POST",
			method: "erpnext.templates.pages.projects.set_"+ item +"_status",
			args: args,
			callback: function(r) {
				if(r.exc) {
					if(r._server_messages)
						frappe.msgprint(r._server_messages);
				} else {
					$(this).remove();
				}
			}
		})
		return false;
	}
});