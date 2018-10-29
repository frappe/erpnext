/**
 * Simple EventEmitter which uses jQuery's event system
 */
class EventEmitter {
    init() {
        this.jq = jQuery(this);
    }

    trigger(evt, data) {
        !this.jq && this.init();
        this.jq.trigger(evt, data);
    }

    once(evt, handler) {
        !this.jq && this.init();
        this.jq.one(evt, (e, data) => handler(data));
    }

    on(evt, handler) {
        !this.jq && this.init();
        this.jq.bind(evt, (e, data) => handler(data));
    }

    off(evt, handler) {
        !this.jq && this.init();
        this.jq.unbind(evt, (e, data) => handler(data));
    }
}


export default EventEmitter;