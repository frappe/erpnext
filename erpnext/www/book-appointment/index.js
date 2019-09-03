
frappe.ready(() => {
    initialise_select_date()
})
var holiday_list = [];

function navigator(page_no) {
    let select_date_div = document.getElementById('select-date');
    select_date_div.style.display = 'none';
    let select_time_div = document.getElementById('select-time');
    select_time_div.style.display = 'none';
    let contact_details_div = document.getElementById('enter-details');
    contact_details_div.style.display = 'none';
    let page;
    switch (page_no) {
        case 1: page = select_date_div; break;
        case 2: page = select_time_div; break;
        case 3: page = contact_details_div; break;
    }
    page.style.display = 'block'
}

// Page 1
async function initialise_select_date() {
    navigator(1);
    let timezones, settings;
    settings = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_appointment_settings'
    })).message
    timezones = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_timezones'
    })).message;
    holiday_list = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_holiday_list',
        args: {
            'holiday_list_name': settings.holiday_list
        }
    })).message;
    let date_picker = document.getElementById('appointment-date');
    date_picker.max = holiday_list.to_date;
    date_picker.min = holiday_list.from_date;
    date_picker.value = (new Date()).toISOString().substr(0, 10);
    let timezones_element = document.getElementById('appointment-timezone');
    var offset = new Date().getTimezoneOffset();
    timezones.forEach(timezone => {
        var opt = document.createElement('option');
        opt.value = timezone.offset;
        opt.innerHTML = timezone.timezone_name;
        opt.defaultSelected = (offset == timezone.offset)
        timezones_element.appendChild(opt)
    });
}

function validate_date() {
    let date_picker = document.getElementById('appointment-date');
    if (date_picker.value === '') {
        frappe.throw('Please select a date')
    }
}

// Page 2
async function navigate_to_time_select() {
    navigator(2);
    timezone = document.getElementById('appointment-timezone').value
    date = document.getElementById('appointment-date').value;
    var date_spans = document.getElementsByClassName('date-span');
    for (var i = 0; i < date_spans.length; i++) date_spans[i].innerHTML = date;
    // date_span.addEventListener('click',initialise_select_date)
    // date_span.style.color = '#5e64ff';
    // date_span.style.textDecoration = 'underline';
    // date_span.style.cursor = 'pointer';
    var slots = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_appointment_slots',
        args: {
            date: date,
            timezone: timezone
        }
    })).message;
    let timeslot_container = document.getElementById('timeslot-container');
    console.log(slots)
    if (slots.length <= 0) {
        let message_div = document.createElement('p');
        
        message_div.innerHTML = "There are no slots available on this date";
        timeslot_container.appendChild(message_div);
    }
    for (let i = 0; i < slots.length; i++) {
        const slot = slots[i];
        var timeslot_div = document.createElement('div');
        timeslot_div.classList.add('time-slot');
        timeslot_div.classList.add('col-md');
        if (!slot.availability) {
            timeslot_div.classList.add('unavailable')
        }
        timeslot_div.innerHTML = slot.time.substr(11, 20);
        timeslot_div.id = slot.time.substr(11, 20);
        timeslot_container.appendChild(timeslot_div);
    }
    set_default_timeslot()
    let time_slot_divs = document.getElementsByClassName('time-slot');
    for (var i = 0; i < time_slot_divs.length; i++) {
        time_slot_divs[i].addEventListener('click', select_time);
    }
}

function select_time() {
    if (this.classList.contains("unavailable")) {
        return
    }
    try {
        selected_element = document.getElementsByClassName('selected')[0]
    } catch (e) {
        this.classList.add("selected")
    }
    selected_element.classList.remove("selected");
    this.classList.add("selected");
}

function set_default_timeslot() {
    let timeslots = document.getElementsByClassName('time-slot')
    for (let i = 0; i < timeslots.length; i++) {
        const timeslot = timeslots[i];
        if (!timeslot.classList.contains('unavailable')) {
            timeslot.classList.add("selected");
            break;
        }
    }
}

function initialise_enter_details() {
    navigator(3);
    let time_div = document.getElementsByClassName('selected')[0];
    let time_span = document.getElementsByClassName('time-span')[0];
    time_span.innerHTML = time_div.id
}

function submit() {
    var date = document.getElementById('appointment-date').value;
    var time = document.getElementsByClassName('selected')[0].id;
    contact = {};
    contact.name = document.getElementById('customer_name').value;
    contact.number = document.getElementById('customer_number').value;
    contact.skype = document.getElementById('customer_skype').value;
    contact.notes = document.getElementById('customer_notes').value;
    console.log({ date, time, contact });
} 
