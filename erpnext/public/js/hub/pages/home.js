import SubPage from './subpage';
import { make_search_bar, get_item_card_container_html } from '../helpers';

erpnext.hub.Home = class Home extends SubPage {
	make_wrapper() {
		super.make_wrapper();

		make_search_bar({
			wrapper: this.$wrapper,
			on_search: keyword => {
				frappe.set_route('marketplace', 'search', keyword);
			}
		});
	}

	refresh() {
		this.get_items_and_render();
	}

	get_items_and_render() {
		this.$wrapper.find('.hub-card-container').empty();
		this.get_data()
			.then(data => {
				this.render(data);
			});
	}

	get_data() {
		return hub.call('get_data_for_homepage', { country: frappe.defaults.get_user_default('country') });
	}

	render(data) {
		let html = get_item_card_container_html(data.random_items, __('Explore'));
		this.$wrapper.append(html);

		if (data.items_by_country.length) {
			html = get_item_card_container_html(data.items_by_country, __('Near you'));
			this.$wrapper.append(html);
		}
	}
}