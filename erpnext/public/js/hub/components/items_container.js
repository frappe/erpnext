import { get_item_card_html } from './item_card';

function get_item_card_container_html(items, title='', get_item_html = get_item_card_html, action='') {
	const items_html = (items || []).map(item => get_item_html(item)).join('');
	const title_html = title
		? `<div class="hub-card-container-header col-sm-12 margin-bottom flex">
				<h4>${title}</h4>
				${action}
			</div>`
		: '';

	const html = `<div class="row hub-card-container">
		${title_html}
		${items_html}
	</div>`;

	return html;
}

export {
	get_item_card_container_html
}
