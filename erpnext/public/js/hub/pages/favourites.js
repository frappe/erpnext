import SubPage from './subpage';
import { get_item_card_container_html } from '../components/items_container';

erpnext.hub.Favourites = class Favourites extends SubPage {
	refresh() {
		this.get_favourites()
			.then(items => {
				this.render(items);
			});
	}

	get_favourites() {
		return hub.call('get_favourite_items_of_seller', {
			hub_seller: hub.settings.company_email
		});
	}

	render(items) {
		this.$wrapper.find('.hub-card-container').empty();
		const html = get_item_card_container_html(items, __('Favourites'));
		this.$wrapper.append(html)
	}
}
