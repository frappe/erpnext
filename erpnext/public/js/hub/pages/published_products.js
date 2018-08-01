import SubPage from './base_page';
import { get_item_card_container_html } from '../helpers';

erpnext.hub.PublishedProducts = class PublishedProducts extends SubPage {
	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_published_products()
			.then(items => this.render(items));
	}

	refresh() {
		this.get_items_and_render();
	}

	render(items) {
		const items_container = $(get_item_card_container_html(items, __('Your Published Products')));
		this.$wrapper.append(items_container);
	}

	get_published_products() {
		return hub.call('get_items_by_seller', { hub_seller: hub.settings.company_email });
	}
}