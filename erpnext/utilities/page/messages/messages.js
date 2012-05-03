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

wn.provide('erpnext.messages');

wn.pages.messages.onload = function(wrapper) {
	erpnext.messages.show_active_users();
	erpnext.messages.make_list();
	erpnext.update_messages('reset'); //Resets notification icons
	
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
	$('#message-post-text').keyup(function(e) {
		if($(this).val()) {
			$('#message-post').attr('disabled', false);
		} else {
			$('#message-post').attr('disabled', true);
		}
		
		if(e.which==13) {
			$('#message-post').click();
		}
	})
}

$(wn.pages.messages).bind('show', function() {
	erpnext.messages.show();
	setTimeout(erpnext.messages.refresh, 7000);
	$('#message-post-text').focus();
})

erpnext.messages = {
	show: function() {
		var contact = erpnext.messages.get_contact();

		// can't send message to self
		$(wn.pages.messages).find('.well').toggle(contact==user ? false : true);

		$(wn.pages.messages).find('h1:first').html('Messages: ' 
			+ (user==contact ? 'From everyone' : wn.user_info(contact).fullname));

		erpnext.messages.contact = contact;
		erpnext.messages.list.opts.args.contact = contact;
		erpnext.messages.list.run();
		
	},
	// check for updates every 5 seconds if page is active
	refresh: function() {
		setTimeout(erpnext.messages.refresh, 7000);
		if(wn.container.page.label != 'Messages') return;
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
		erpnext.messages.list = new wn.ui.Listing({
			parent: $('#message-list').get(0),
			method: 'utilities.page.messages.messages.get_list',
			args: {
				contact: null
			},
			render_row: function(wrapper, data) {
				$(wrapper).removeClass('list-row');
				
				data.creation = dateutil.comment_when(data.creation);
				data.comment_by_fullname = wn.user_info(data.owner).fullname;

				data.reply_html = '';
				if(data.owner==user) {
					data.cls = 'message-self';
					data.comment_by_fullname = 'You';	
					data.delete_html = repl('<a class="close" \
						onclick="erpnext.messages.delete(this)"\
						data-name="%(name)s">&times;</a>', data);
				} else {
					data.cls = 'message-other';
					data.delete_html = '';
					if(erpnext.messages.contact==user) {
						data.reply_html = repl('<a href="#!messages/%(owner)s">\
							<i class="icon-share-alt"></i> Reply</a>', data)
					}
				}

				wrapper.innerHTML = repl('<div class="message %(cls)s">%(delete_html)s\
						<b>%(comment)s</b>\
						<div class="help">by %(comment_by_fullname)s, %(creation)s</div>\
						%(reply_html)s</div>\
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
					p.fullname = wn.user_info(p.name).fullname;
					p.name = p.name.replace('@', '__at__');
					$body.append(repl('<div class="section-item">\
						<a href="#!messages/%(name)s">%(fullname)s</a></div>', p))
				}
			}
		});
	}
}


