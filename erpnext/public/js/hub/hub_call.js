frappe.provide('hub');
frappe.provide('erpnext.hub');

erpnext.hub.cache = {};
hub.call = function call_hub_method(method, args={}) {
	return new Promise((resolve, reject) => {

		// cache
		const key = method + JSON.stringify(args);
		if (erpnext.hub.cache[key]) {
			resolve(erpnext.hub.cache[key]);
		}

		// cache invalidation after 5 minutes
		const timeout = 5 * 60 * 1000;

		setTimeout(() => {
			delete erpnext.hub.cache[key];
		}, timeout);

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
				resolve(r.message)
			}
			reject(r)
		})
		.fail(reject)
	});
}
