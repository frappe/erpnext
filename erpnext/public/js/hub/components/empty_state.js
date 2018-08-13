function get_empty_state(message, action) {
	return `<div class="empty-state flex align-center flex-column justify-center">
		<p class="text-muted">${message}</p>
		${action ? `<p>${action}</p>`: ''}
	</div>`;
}

export {
    get_empty_state
}
