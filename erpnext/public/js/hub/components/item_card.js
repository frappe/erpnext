function get_buying_item_message_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);

	const message = item.recent_message
	const sender = message.sender === frappe.session.user ? 'You' : message.sender
	const content = strip_html(message.content)

	// route
	item.route = `marketplace/buying/${item.name}`

	const item_html = `
		<div class="col-md-7">
			<div class="hub-list-item" data-route="${item.route}">
				<div class="hub-list-left">
					<img class="hub-list-image" src="${item.image}">
					<div class="hub-list-body ellipsis">
						<div class="hub-list-title">${item_name}</div>
						<div class="hub-list-subtitle ellipsis">
							<span>${sender}: </span>
							<span>${content}</span>
						</div>
					</div>
				</div>
				<div class="hub-list-right">
					<span class="text-muted">${comment_when(message.creation, true)}</span>
				</div>
			</div>
		</div>
	`;

	return item_html;
}

function get_selling_item_message_card_html(item) {
	const item_name = item.item_name || item.name;
	const title = strip_html(item_name);

	// route
	if (!item.route) {
		item.route = `marketplace/item/${item.name}`
	}

	let received_messages = '';
	item.received_messages.forEach(message => {
		const sender = message.sender === frappe.session.user ? 'You' : message.sender
		const content = strip_html(message.content)

		received_messages += `
			<div class="received-message">
				<span class="text-muted">${comment_when(message.creation, true)}</span>
				<div class="ellipsis">
					<span class="bold">${sender}: </span>
					<span>${content}</span>
				</div>
			</div>
		`
	});

	const item_html = `
		<div class="selling-item-message-card">
			<div class="selling-item-detail" data-route="${item.route}">
				<img class="item-image" src="${item.image}">
				<h5 class="item-name">${item_name}</h5>
				<div class="received-message-container">
					${received_messages}
				</div>
			</div>
		</div>
	`;

	return item_html;
}

export {
	get_item_card_html,
	get_local_item_card_html,
	get_buying_item_message_card_html,
	get_selling_item_message_card_html
}
