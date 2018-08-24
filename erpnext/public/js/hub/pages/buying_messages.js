import SubPage from './subpage';

erpnext.hub.MessageList = class BuyingMessages extends SubPage {
	make_wrapper() {
		const messages_of = this.options[0];
		if (messages_of === 'Buying') {
			this.back_route = 'marketplace/buying-messages'
		} else {
			this.back_route = 'marketplace/selling-messages'
		}
		super.make_wrapper();
		this.add_back_link(__('Back to Messages'), this.back_route);
		this.$message_container = this.add_section({ title: 'Buy' });
	}

	refresh() {
		const item_code = frappe.get_route()[2] || null;
		if (!item_code) {
			frappe.set_route(this.back_route);
			return;
		}
		this.get_item_details(item_code)
			.then(item_details => {
				this.item_details = item_details;
				this.$message_container.find('.hub-section-header h4').text(this.item_details.item_name);

				// make chat area
				this.$message_container.find('.hub-section-body').html(`
					<div class="col-md-7 message-container">
						<div class="message-list"></div>
						<div class="message-input"></div>
					</div>
				`)
				this.make_message_input();

				// fetch messages
				this.get_messages(item_details)
					.then(messages => {
						const $message_list = this.$message_container.find('.message-list');
						const html = messages.map(get_message_html).join('');
						$message_list.html(html);
						frappe.dom.scroll_to_bottom($message_list);
					});
			});

	}

	get_messages(item_details) {
		 return hub.call('get_messages', {
			against_seller: item_details.hub_seller,
			against_item: item_details.hub_item_code
		});
	}

	get_item_details(hub_item_code) {
		return hub.call('get_item_details', { hub_item_code })
	}

	make_message_input() {
		this.message_input = new frappe.ui.CommentArea({
			parent: this.$message_container.find('.message-input'),
			on_submit: (message) => {
				this.message_input.reset();

				// append message html
				const $message_list = this.$message_container.find('.message-list');
				const message_html = get_message_html({
					sender: hub.settings.company_email,
					content: message
				});
				$message_list.append(message_html);
				frappe.dom.scroll_to_bottom($message_list);

				// send message
				hub.call('send_message', {
					from_seller: hub.settings.company_email,
					to_seller: this.item_details.hub_seller,
					hub_item: this.item_details.hub_item_code,
					message
				});
			},
			no_wrapper: true
		});
	}
}

function get_message_html(message) {
	return `
		<div class="level margin-bottom">
			<div class="level-left ellipsis" style="width: 80%;">
				${frappe.avatar(message.sender)}
				<div style="white-space: normal;">
					${message.content}
				</div>
			</div>
			<div class="level-right text-muted">
				${comment_when(message.creation, true)}
			</div>
		</div>
	`;
}