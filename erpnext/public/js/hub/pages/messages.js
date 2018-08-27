import SubPage from './subpage';
// import { get_item_card_container_html } from '../components/items_container';
import { get_buying_item_message_card_html } from '../components/item_card';
import { get_selling_item_message_card_html } from '../components/item_card';
// import { get_empty_state } from '../components/empty_state';

erpnext.hub.Buying = class Buying extends SubPage {
	refresh() {
		this.get_items_for_messages().then((items) => {
			this.empty();
			if (items.length) {
				items.map(item => {
					item.route = `marketplace/buying/${item.hub_item_code}`
				})
				this.render(items, __('Buying'));
			}

			if (!items.length && !items.length) {
				this.render_empty_state();
			}
		});
	}

	render(items = [], title) {
		// const html = get_item_card_container_html(items, title, get_buying_item_message_card_html);
		this.$wrapper.append(html);
	}

	render_empty_state() {
		// const empty_state = get_empty_state(__('You haven\'t interacted with any seller yet.'));
		// this.$wrapper.html(empty_state);
	}

	get_items_for_messages() {
		return hub.call('get_buying_items_for_messages', {}, 'action:send_message');
	}
}

erpnext.hub.Selling = class Selling extends SubPage {
	refresh() {
		this.get_items_for_messages().then((items) => {
			this.empty();
			if (items.length) {
				items.map(item => {
					item.route = `marketplace/selling/${item.hub_item_code}`
				})
				this.render(items, __('Selling'));
			}

			if (!items.length && !items.length) {
				this.render_empty_state();
			}
		});
	}

	render(items = [], title) {
		// const html = get_item_card_container_html(items, title, get_selling_item_message_card_html);
		this.$wrapper.append(html);
	}

	render_empty_state() {
		const empty_state = get_empty_state(__('You haven\'t interacted with any seller yet.'));
		this.$wrapper.html(empty_state);
	}

	get_items_for_messages() {
		return hub.call('get_selling_items_for_messages', {});
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
