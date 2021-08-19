// ruleid: frappe-translation-empty-string
__("")
// ruleid: frappe-translation-empty-string
__('')

// ok: frappe-translation-js-formatting
__('Welcome {0}, get started with ERPNext in just a few clicks.', [full_name]);

// ruleid: frappe-translation-js-formatting
__(`Welcome ${full_name}, get started with ERPNext in just a few clicks.`);

// ok: frappe-translation-js-formatting
__('This is fine');


// ok: frappe-translation-trailing-spaces
__('This is fine');

// ruleid: frappe-translation-trailing-spaces
__(' this is not ok ');
// ruleid: frappe-translation-trailing-spaces
__('this is not ok ');
// ruleid: frappe-translation-trailing-spaces
__(' this is not ok');

// ok: frappe-translation-js-splitting
__('You have {0} subscribers in your mailing list.', [subscribers.length])

// todoruleid: frappe-translation-js-splitting
__('You have') + subscribers.length + __('subscribers in your mailing list.')

// ruleid: frappe-translation-js-splitting
__('You have' + 'subscribers in your mailing list.')

// ruleid: frappe-translation-js-splitting
__('You have {0} subscribers' +
    'in your mailing list', [subscribers.length])

// ok: frappe-translation-js-splitting
__("Ctrl+Enter to add comment")

// ruleid: frappe-translation-js-splitting
__('You have {0} subscribers \
    in your mailing list', [subscribers.length])
