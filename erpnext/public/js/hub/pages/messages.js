import SubPage from './subpage';
import { get_item_card_container_html } from '../components/items_container';
import { get_empty_state } from '../components/empty_state';

erpnext.hub.Messages = class Messages extends SubPage {
	make_wrapper() {
		super.make_wrapper();
	}

	refresh() {
		const messages_of = this.options[0];
		this.get_items_for_messages(messages_of).then((items) => {
			this.empty();
			if (items.length) {
				items.map(item => {
					item.route = `marketplace/${messages_of.toLowerCase()}/${item.hub_item_code}`
				})
				this.render(items, __(messages_of));
			}

			if (!items.length && !items.length) {
				this.render_empty_state();
			}
		});
	}

	render(items = [], title) {
		const html = get_item_card_container_html(items, title);
		this.$wrapper.append(html);
	}

	render_empty_state() {
		const empty_state = get_empty_state(__('You haven\'t interacted with any seller yet.'));
		this.$wrapper.html(empty_state);
	}

	get_items_for_messages(messages_of) {
		if (messages_of === 'Buying') {
			return hub.call('get_buying_items_for_messages', {}, 'action:send_message');
		} else if (messages_of === 'Selling') {
			return hub.call('get_selling_items_for_messages');
		} else {
			frappe.throw('Invalid message type');
		}
	}

	get_interactions() {
		return hub.call('get_sellers_with_interactions', { for_seller: hub.settings.company_email });
	}
}

function get_message_area_html() {
	return `
		<div class="message-area border padding flex flex-column">
			<div class="message-list">
			</div>
			<div class="message-input">
			</div>
		</div>
	`;
}

function get_list_item_html(seller) {
	const active_class = frappe.get_route()[2] === seller.email ? 'active' : '';

	return `
		<div class="message-list-item ${active_class}" data-route="marketplace/messages/${seller.email}">
			<div class="list-item-left">
				<img src="${seller.image || 'https://picsum.photos/200?random'}">
			</div>
			<div class="list-item-body">
				${seller.company}
			</div>
		</div>
	`;
}

function get_message_html(message) {
	return `
		<div>
			<h5>${message.sender}</h5>
			<p>${message.content}</p>
		</div>
	`;
}
