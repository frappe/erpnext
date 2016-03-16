frappe.ready(function() {
	var reload_tasks = function(taskstatus) {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_tasks_html",
				project: '{{ doc.name }}',
				taskstatus: taskstatus,
			},
			dataType: "json",
			success: function(data) {
				$('.project-tasks').html(data.message);
				
				$('.project-tasks-section .btn-group .btn-primary').removeClass('btn-primary');
				$('.btn-'+ taskstatus +'-tasks').addClass( "btn-primary" );
			}
		});	
		
	}
	
	$('.btn-closed-tasks').click(function() {
		reload_tasks('closed');
	});	
	$('.btn-open-tasks').click(function() {
		reload_tasks('open');
	});
	
	var reload_issues = function(issuestatus) {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_issues_html",
				project: '{{ doc.name }}',
				issuestatus: issuestatus,
			},
			dataType: "json",
			success: function(data) {
				$('.project-issues').html(data.message);
				
				$('.project-issues-section .btn-group .btn-primary').removeClass('btn-primary');
				$('.btn-'+ issuestatus +'-issues').addClass( "btn-primary" );
			}
		});	
		
	}
	
	$('.btn-closed-issues').click(function() {
		reload_issues('closed');
	});	
	$('.btn-open-issues').click(function() {
		reload_issues('open');
	});

	var taskstart = 5;
	$(".more-tasks").click(function() {
		var task_status = $('.project-tasks-section .btn-group .btn-primary').hasClass('btn-closed-tasks') 
			? 'closed' : 'open';

		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_tasks_html",
				project: '{{ doc.name }}',
				start: taskstart,
				taskstatus: task_status,
			},
			dataType: "json",
			success: function(data) {
				$(data.message).appendTo('.project-tasks');
				if(typeof data.message == 'undefined') {	
					$(".more-tasks").toggle(false);	
				}
			taskstart = taskstart+5;
			}
		});	
			
	});
	
	var issuestart = 2;
	$(".more-issues").click(function() {
		var issue_status = $('.project-issues-section .btn-group .btn-primary').hasClass('btn-closed-issues') 
			? 'closed' : 'open';
		
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_issues_html",
				project: '{{ doc.name }}',
				start: issuestart,
				issuestatus: issue_status,
			},
			dataType: "json",
			success: function(data) {
				$(data.message).appendTo('.project-issues');
				if(typeof data.message == 'undefined')
				{	
					$(".more-issues").toggle(false);
				}
				issuestart = issuestart+5;
			}
		});	
	});
	
	var timelogstart = 2;
	$(".more-timelogs").click(function() {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_timelogs_html",
				project: '{{ doc.name }}',
				start: timelogstart,
			},
			dataType: "json",
			success: function(data) {
				$(data.message).appendTo('.project-timelogs');
				if(typeof data.message == 'undefined')
				{	
					$(".more-timelogs").toggle(false);	
				}
				timelogstart = timelogstart+2;
				
			}
		});	
			
	});
	
	var timelinestart = 10;
	$(".more-timelines").click(function() {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_timeline_html",
				project: '{{ doc.name }}',
				start: timelinestart,
				
			},
			dataType: "json",
			success: function(data) {
				$(data.message).appendTo('.project-timeline');
				if(typeof data.message == 'undefined')
				{	
					$(".more-timelines").toggle(false);
				}
				timelinestart = timelinestart+10;
			}
		});	
	});	
		
	$( ".project-tasks" ).on('click', '.task-x', function() {
		var args = {
			project: '{{ doc.name }}',
			task_name: $(this).attr('id'),
		}
		frappe.call({
			btn: this,
			type: "POST",
			method: "erpnext.templates.pages.projects.set_task_status",
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
	});	
		
	$( ".project-issues" ).on('click', '.issue-x', function() {
		var args = {
			project: '{{ doc.name }}',
			issue_name: $(this).attr('id'),
		}
		frappe.call({
			btn: this,
			type: "POST",
			method: "erpnext.templates.pages.projects.set_issue_status",
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
	});		
});
