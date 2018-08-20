frappe.provide('hub');
frappe.provide('erpnext.hub');

erpnext.hub.cache = {};
hub.call = function call_hub_method(method, args={}, setup_cache_invalidation = invalidate_after_5_mins) {
	return new Promise((resolve, reject) => {

		// cache
		const key = method + JSON.stringify(args);
		if (erpnext.hub.cache[key]) {
			resolve(erpnext.hub.cache[key]);
		}

		// cache invalidation
		const clear_cache = () => delete erpnext.hub.cache[key];
		setup_cache_invalidation(clear_cache);

		frappe.call({
			method: 'erpnext.hub_node.api.call_hub_method',
			args: {
				method,
				params: args
			}
		})
		.then(r => {
			if (r.message) {
				if (r.message.error) {
					frappe.throw({
						title: __('Marketplace Error'),
						message: r.message.error
					});
				}

				erpnext.hub.cache[key] = r.message;
				erpnext.hub.trigger(`response:${key}`);
				resolve(r.message);
			}
			reject(r);
		})
		.fail(reject)
	});
}

function invalidate_after_5_mins(clear_cache) {
	// cache invalidation after 5 minutes
	const timeout = 5 * 60 * 1000;

	setTimeout(() => {
		clear_cache();
	}, timeout);
}
