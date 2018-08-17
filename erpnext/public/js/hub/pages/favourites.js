import SubPage from './subpage';
import { get_item_card_container_html } from '../components/items_container';

erpnext.hub.Favourites = class Favourites extends SubPage {
	make_wrapper() {
		super.make_wrapper();
		this.bind_events();
	}

	bind_events() {
		this.$wrapper.on('click', '.hub-card', (e) => {
			const $target = $(e.target);
			if($target.hasClass('octicon-x')) {
				e.stopPropagation();
				const hub_item_code = $target.attr('data-hub-item-code');
				this.on_item_remove(hub_item_code);
			}
		});
	}

	refresh() {
		this.get_favourites()
			.then(items => {
				this.render(items);
			});
	}

	get_favourites() {
		return hub.call('get_favourite_items_of_seller', {
			hub_seller: hub.settings.company_email
		}, 'action:item_favourite');
	}

	render(items) {
		this.$wrapper.find('.hub-items-container').empty();
		const html = get_item_card_container_html(items, __('Favourites'));
		this.$wrapper.html(html);
		this.$wrapper.find('.hub-card').addClass('closable');

		if (!items.length) {
			this.render_empty_state();
		}
	}

	render_empty_state() {
		this.$wrapper.find('.hub-items-container').append(`
			<div class="col-md-12">${__("You don't have any favourites yet.")}</div>
		`)
	}

	on_item_remove(hub_item_code, $hub_card = '') {
		const $message = $(__(`<span>${hub_item_code} removed.
			<a href="#" data-action="undo-remove"><b>Undo</b></a></span>`));

		frappe.show_alert($message);

		$hub_card = this.$wrapper.find(`.hub-card[data-hub-item-code="${hub_item_code}"]`);

		$hub_card.hide();

		const grace_period = 5000;

		setTimeout(() => {
			this.remove_item(hub_item_code, $hub_card);
		}, grace_period);
	}

	remove_item(hub_item_code, $hub_card) {
		hub.call('remove_item_from_seller_favourites', {
			hub_item_code,
			hub_seller: hub.settings.company_email
		})
		.then(() => {
			$hub_card.remove();
		})
		.catch(e => {
			console.log(e);
		});
	}

	undo_remove(hub_item_code) { }
}
