
frappe.ready(() => {
    initialise_select_date()
})
window.holiday_list = [];

async function initialise_select_date() {
    document.getElementById('enter-details').style.display = 'none';
    await get_global_variables();
    setup_date_picker();
    setup_timezone_selector();
    hide_next_button();
}

async function get_global_variables() {
    window.appointment_settings = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_appointment_settings'
    })).message
    window.timezones = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_timezones'
    })).message;
    window.holiday_list = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_holiday_list',
        args: {
            'holiday_list_name': window.appointment_settings.holiday_list
        }
    })).message;
}

function setup_timezone_selector() {
    let timezones_element = document.getElementById('appointment-timezone');
    var offset = new Date().getTimezoneOffset();
    window.timezones.forEach(timezone => {
        var opt = document.createElement('option');
        opt.value = timezone.offset;
        opt.innerHTML = timezone.timezone_name;
        opt.defaultSelected = (offset == timezone.offset)
        timezones_element.appendChild(opt)
    });
}

function setup_date_picker() {
    let date_picker = document.getElementById('appointment-date');
    let today = new Date();
    date_picker.min = today.toISOString().substr(0, 10);
    date_picker.max = window.holiday_list.to_date;
}

function hide_next_button(){
    let next_button = document.getElementById('next-button');
    next_button.disabled = true;
    next_button.onclick = ()=>{frappe.msgprint("Please select a date and time")};
}

function show_next_button(){
    let next_button = document.getElementById('next-button');
    next_button.disabled = false;
    next_button.onclick = setup_details_page;
}

function on_date_or_timezone_select() {
    let date_picker = document.getElementById('appointment-date');
    let timezone = document.getElementById('appointment-timezone');
    if (date_picker.value === '') {
        clear_time_slots();
        hide_next_button();
        frappe.throw('Please select a date');
    }
    window.selected_date = date_picker.value;
    window.selected_timezone = timezone.value;
    update_time_slots(date_picker.value, timezone.value);
}

async function get_time_slots(date, timezone) {
    debugger
    let slots = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.get_appointment_slots',
        args: {
            date: date,
            timezone: timezone
        }
    })).message;
    return slots;
}

async function update_time_slots(selected_date, selected_timezone) {
    let timeslot_container = document.getElementById('timeslot-container');
    window.slots = await get_time_slots(selected_date, selected_timezone);
    clear_time_slots();
    if (window.slots.length <= 0) {
        let message_div = document.createElement('p');
        message_div.innerHTML = "There are no slots available on this date";
        timeslot_container.appendChild(message_div);
        return
    }
    window.slots.forEach(slot => {
        let start_time = new Date(slot.time)
        var timeslot_div = document.createElement('div');
        timeslot_div.classList.add('time-slot');
        timeslot_div.classList.add('col-md');
        if (!slot.availability) {
            timeslot_div.classList.add('unavailable')
        }
        timeslot_div.innerHTML = get_slot_layout(start_time);
        timeslot_div.id = slot.time.substr(11, 20);
        timeslot_div.addEventListener('click', select_time);
        timeslot_container.appendChild(timeslot_div);
    });
    set_default_timeslot();
    show_next_button();
}

function clear_time_slots() {
    let timeslot_container = document.getElementById('timeslot-container');
    while (timeslot_container.firstChild) {
        timeslot_container.removeChild(timeslot_container.firstChild)
    }
}

function get_slot_layout(time) {
    time = new Date(time)
    let start_time_string = moment(time).format("LT");
    let end_time = moment(time).add('1','hours');
    let end_time_string = end_time.format("LT");
    return `<span style="font-size: 1.2em;">${start_time_string}</span><br><span class="text-muted small">to ${end_time_string}</span>`;
}

function select_time() {
    if (this.classList.contains("unavailable")) {
        return
    }
    try {
        selected_element = document.getElementsByClassName('selected')[0]
    } catch (e) {
        debugger
        this.classList.add("selected")
    }
    window.selected_time = this.id
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

function setup_details_page(){
    let page1 = document.getElementById('select-date-time');
    let page2 = document.getElementById('enter-details');
    page1.style.display = 'none';
    page2.style.display = 'block';

    let date_container = document.getElementsByClassName('date-span')[0];
    let time_container = document.getElementsByClassName('time-span')[0];

    date_container.innerHTML = new Date(window.selected_date).toLocaleDateString();
    time_container.innerHTML = moment(window.selected_time,"HH:mm:ss").format("LT");
}

async function submit() {
    // form validation here
    form_validation();
    let appointment = (await frappe.call({
        method: 'erpnext.www.book-appointment.index.create_appointment',
        args: {
            'date': date,
            'time': time,
            'contact': contact
        }
    })).message;
    frappe.msgprint(__('Appointment Created Successfully'));
    let button = document.getElementById('submit-button');
    button.disabled = true;
    button.onclick = () => { console.log('This should never have happened') }
} 

function form_validation(){
    var date = window.selected_date;
    var time = document.getElementsByClassName('selected')[0].id;
    contact = {};
    contact.name = document.getElementById('customer_name').value;
    contact.number = document.getElementById('customer_number').value;
    contact.skype = document.getElementById('customer_skype').value;
    contact.notes = document.getElementById('customer_notes').value;
    window.contact = contact
    console.log({ date, time, contact });
}
