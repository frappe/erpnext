import SubPage from './subpage';
import { make_search_bar } from '../components/search_bar';

erpnext.hub.Messages = class Messages extends SubPage {
    make_wrapper() {
        super.make_wrapper();

        const html = `
            <div class="row">
                <div class="col-md-5">
                    <div class="seller-list"></div>
                </div>
                <div class="col-md-7">
                    ${get_message_area_html()}
                </div>
            </div>
        `;

        make_search_bar({
            wrapper: this.$wrapper,
            on_search: keyword => {

            },
            placeholder: __('Search for messages')
        })

        this.$wrapper.append(html);

        this.message_input = new frappe.ui.CommentArea({
            parent: this.$wrapper.find('.message-input'),
            on_submit: (message) => {
                this.message_input.reset();

                // append message html
                const $message_list = this.$wrapper.find('.message-list');
                const message_html = get_message_html({
                    sender: hub.settings.company_email,
                    content: message
                });
                $message_list.append(message_html);
                frappe.dom.scroll_to_bottom($message_list);

                const to_seller = frappe.get_route()[2];
                hub.call('send_message', {
                    from_seller: hub.settings.company_email,
                    to_seller,
                    message
                });
            },
            no_wrapper: true
        });
    }

    refresh() {
        this.get_interactions()
            .then(sellers => {
                const html = sellers.map(get_list_item_html).join('');
                this.$wrapper.find('.seller-list').html(html);
            });

        this.get_messages()
            .then(messages => {
                const $message_list = this.$wrapper.find('.message-list');
                const html = messages.map(get_message_html).join('');
                $message_list.html(html);
                frappe.dom.scroll_to_bottom($message_list);
            });
    }

    get_interactions() {
        return hub.call('get_sellers_with_interactions', { for_seller: hub.settings.company_email });
    }

    get_messages() {
        const against_seller = frappe.get_route()[2];
        if (!against_seller) return Promise.resolve([]);

        return hub.call('get_messages', {
            for_seller: hub.settings.company_email,
            against_seller: against_seller
        });
    }
}

function get_message_area_html() {
    return `
        <div class="message-area border padding flex flex-column">
            <div class="message-list">
            </div>
            <div class="message-input">
            </div>
        </div>
    `;
}

function get_list_item_html(seller) {
    const active_class = frappe.get_route()[2] === seller.email ? 'active' : '';

    return `
        <div class="message-list-item ${active_class}" data-route="marketplace/messages/${seller.email}">
            <div class="list-item-left">
                <img src="${seller.image || 'https://picsum.photos/200?random'}">
            </div>
            <div class="list-item-body">
                ${seller.company}
            </div>
        </div>
    `;
}

function get_message_html(message) {
    return `
        <div>
            <h5>${message.sender}</h5>
            <p>${message.content}</p>
        </div>
    `;
}
