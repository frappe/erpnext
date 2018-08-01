import SubPage from './base_page';
import { get_item_card_container_html } from '../helpers';

erpnext.hub.Favourites = class Favourites extends SubPage {
	refresh() {
		this.get_favourites()
			.then(items => {
				this.render(items);
			});
	}

	get_favourites() {
		return hub.call('get_item_favourites');
	}

	render(items) {
		this.$wrapper.find('.hub-card-container').empty();
		const html = get_item_card_container_html(items, __('Favourites'));
		this.$wrapper.append(html)
	}
}