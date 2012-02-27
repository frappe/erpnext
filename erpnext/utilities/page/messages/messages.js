wn.provide('erpnext.messages');

wn.pages.messages.onload = function(wrapper) {
	erpnext.messages.show_active_users();
	erpnext.messages.make_list();
	
	// post message
	$('#message-post').click(function() {
		var txt = $('#message-post-text').val();
		if(txt) {
			wn.call({
				module:'utilities',
				page:'messages',
				method:'post',
				args: {
					txt: txt,
					contact: erpnext.messages.contact
				},
				callback:function(r,rt) {
					$('#message-post-text').val('')
					erpnext.messages.list.run();
				},
				btn: this
			});
		}
	});
	
	// enable, disable button
	$('#message-post-text').keyup(function() {
		if($(this).val()) {
			$('#message-post').attr('disabled', false);
		} else {
			$('#message-post').attr('disabled', true);
		}
	})
}

wn.pages.messages.onshow = function(wrapper) {
	erpnext.messages.show();
	setTimeout(erpnext.messages.refresh, 5000);
}

erpnext.messages = {
	show: function() {
		var contact = erpnext.messages.get_contact();

		// can't send message to self
		$(wn.pages.messages).find('.well').toggle(contact==user ? false : true);

		$(wn.pages.messages).find('h1:first').html('Messages: ' 
			+ (user==contact ? 'From everyone' : wn.boot.user_fullnames[contact]))

		erpnext.messages.contact = contact;
		erpnext.messages.list.opts.args.contact = contact;
		erpnext.messages.list.run();
		
	},
	// check for updates every 5 seconds if page is active
	refresh: function() {
		setTimeout(erpnext.messages.refresh, 10000);
		if(page_body.cur_page_label != 'messages') return;
		erpnext.messages.show();
	},
	get_contact: function() {
		var route = location.hash;
		if(route.indexOf('/')!=-1) {
			var name = decodeURIComponent(route.split('/')[1]);
			if(name.indexOf('__at__')!=-1) {
				name = name.replace('__at__', '@');
			}
			return name;
		}
		return user;	
	},
	make_list: function() {
		erpnext.messages.list = new wn.widgets.Listing({
			parent: $('#message-list').get(0),
			method: 'utilities.page.messages.messages.get_list',
			args: {
				contact: null
			},
			render_row: function(wrapper, data) {
				data.creation = dateutil.comment_when(data.creation);
				data.comment_by_fullname = wn.boot.user_fullnames[data.owner];

				if(data.owner==user) {
					data.cls = 'message-self';
					data.comment_by_fullname = 'You';	
					data.delete_html = repl('<a class="close" onclick="erpnext.messages.delete(this)"\
						data-name="%(name)s">&times;</a>', data);
				} else {
					data.cls = 'message-other';
					data.delete_html = '';
				}

				wrapper.innerHTML = repl('<div class="message %(cls)s">%(delete_html)s\
						<b>%(comment)s</b>\
						<div class="help">by %(comment_by_fullname)s, %(creation)s</div></div>\
					<div style="clear: both;"></div>', data);
			}
		});
	},
	delete: function(ele) {
		$(ele).parent().css('opacity', 0.6);
		wn.call({
			method:'utilities.page.messages.messages.delete',
			args: {name : $(ele).attr('data-name')},
			callback: function() {
				$(ele).parent().toggle(false);
			}
		});
	},
	show_active_users: function() {
		wn.call({
			module:'utilities',
			page:'messages',
			method:'get_active_users',
			callback: function(r,rt) {
				var $body = $(wn.pages.messages).find('.section-body');
				for(var i in r.message) {
					var p = r.message[i];
					p.fullname = wn.boot.user_fullnames[p.name];
					p.name = p.name.replace('@', '__at__');
					$body.append(repl('<div class="section-item">\
						<a href="#!messages/%(name)s">%(fullname)s</a></div>', p))
				}
			}
		});
	}
}


