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
	wn.ui.make_app_page({
		parent: wrapper,
		title: "Messages"
	});
	
	$('<h3 id="message-title">Everyone</h3>\
	<div id="show-everyone" style="display: none;">\
		<a href="#messages" style="font-size: 80%;">\
			Show messages from everyone</a></div><hr>\
	<div id="post-message" style="display: none">\
	<textarea style="width: 100%; height: 24px;"></textarea>\
	<div><button class="btn btn-small">Post</button></div><hr>\
	</div>\
	<div class="all-messages"></div>').appendTo($(wrapper).find('.layout-main-section'));
	
	erpnext.messages = new erpnext.Messages(wrapper);
}

$(wn.pages.messages).bind('show', function() {
	erpnext.messages.show();
	setTimeout("erpnext.messages.refresh()", 7000);
})

erpnext.Messages = Class.extend({
	init: function(wrapper) {
		this.wrapper = wrapper;
		this.show_active_users();
		this.make_post_message();
		this.make_list();
		//this.update_messages('reset'); //Resets notification icons		
	},
	make_post_message: function() {
		var me = this;
		$('#post-message textarea').keydown(function(e) {
			if(e.which==13) {
				$('#post-message .btn').click();
				return false;
			}
		});
		
		$('#post-message .btn').click(function() {
			var txt = $('#post-message textarea').val();
			if(txt) {
				wn.call({
					module:'utilities',
					page:'messages',
					method:'post',
					args: {
						txt: txt,
						contact: me.contact
					},
					callback:function(r,rt) {
						$('#post-message textarea').val('')
						me.list.run();
					},
					btn: this
				});
			}			
		});
	},
	show: function() {
		var contact = this.get_contact();

		$('#message-title').text(contact==user ? "Everyone" :
			wn.boot.user_info[contact].fullname)

		$("#show-everyone").toggle(contact!=user);
		
		// can't send message to self
		$('#post-message').toggle(contact!=user);

		this.contact = contact;
		this.list.opts.args.contact = contact;
		this.list.run();
		
	},
	// check for updates every 5 seconds if page is active
	refresh: function() {
		setTimeout("erpnext.messages.refresh()", 7000);
		if(wn.container.page.label != 'Messages') return;
		this.show();
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
		this.list = new wn.ui.Listing({
			parent: $(this.wrapper).find('.all-messages'),
			method: 'utilities.page.messages.messages.get_list',
			args: {
				contact: null
			},
			hide_refresh: true,
			no_loading: true,
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
					if(this.contact==user) {
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
		var me = this;
		wn.call({
			module:'utilities',
			page:'messages',
			method:'get_active_users',
			callback: function(r,rt) {
				var $body = $(me.wrapper).find('.layout-side-section');
				$("<h4>Users</h4><hr>").appendTo($body);
				for(var i in r.message) {
					var p = r.message[i];
					if(p.name != user) {
						p.fullname = wn.user_info(p.name).fullname;
						p.name = p.name.replace('@', '__at__');
						p.label_status = p.has_session ? "label-success" : "";
						p.status = p.has_session ? "Online" : "Offline";
						$(repl('<p><span class="label %(label_status)s">%(status)s</span>\
							<a href="#!messages/%(name)s">%(fullname)s</a>\
							</p>', p))
							.appendTo($body);						
					}
				}
			}
		});
	}
});


