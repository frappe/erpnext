frappe.ready(function() {

	$('.task-status-switch').on('click', function() {
		var $btn = $(this);
		if($btn.attr('data-status')==='Open') {
			reload_items('completed', 'task', $btn);
		} else {
			reload_items('open', 'task', $btn);
		}
	})


	$('.issue-status-switch').on('click', function() {
		var $btn = $(this);
		if($btn.attr('data-status')==='Open') {
			reload_items('completed', 'issue', $btn);
		} else {
			reload_items('open', 'issue', $btn);
		}
	})

	var start = 10;
	$(".more-tasks").click(function() {
		more_items('task', true);
	});

	$(".more-issues").click(function() {
		more_items('issue', true);
	});

	$(".more-timelogs").click(function() {
		more_items('timelog', false);
	});

	$(".more-timelines").click(function() {
		more_items('timeline', false);
	});

	$(".file-size").each(function() {
		$(this).text(frappe.form.formatters.FileSize($(this).text()));
	});


	var reload_items = function(item_status, item, $btn) {
		$.ajax({
			method: "GET",
			url: "/",
			dataType: "json",
			data: {
				cmd: "erpnext.templates.pages.projects.get_"+ item +"_html",
				project: '{{ doc.name }}',
				item_status: item_status,
			},
			success: function(data) {
				if(typeof data.message == 'undefined') {
					$('.project-'+ item).html("No "+ item_status +" "+ item);
					$(".more-"+ item).toggle(false);
				}
				$('.project-'+ item).html(data.message);
				$(".more-"+ item).toggle(true);

				// update status
				if(item_status==='open') {
					$btn.html(__('Show Completed')).attr('data-status', 'Open');
				} else {
					$btn.html(__('Show Open')).attr('data-status', 'Completed');
				}
			}
		});

	}

	var more_items = function(item, item_status){
		if(item_status) {
			var item_status = $('.project-'+ item +'-section .btn-group .bold').hasClass('btn-completed-'+ item)
				? 'completed' : 'open';
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
