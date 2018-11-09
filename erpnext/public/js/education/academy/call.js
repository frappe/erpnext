frappe.provide('academy');

academy.call = (method, args) => {
    const method_path = 'erpnext.www.academy.' + method;
    return new Promise((resolve, reject) => {
        return frappe.call({
            method: method_path,
            args,
        })
        .then(r => resolve(r.message))
        .fail(reject)
    });
}