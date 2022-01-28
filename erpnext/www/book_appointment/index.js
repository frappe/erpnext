frappe.ready(async () => {
    initialise_select_date();
})

window.holiday_list = [];

async function initialise_select_date() {
    navigate_to_page(1);
    await get_global_variables();
    setup_date_picker();
    setup_timezone_selector();
    hide_next_button();
}

async function get_global_variables() {
    // Using await through this file instead of then.
    window.appointment_settings = (await frappe.call({
        method: 'erpnext.www.book_appointment.index.get_appointment_settings'
    })).message;
    window.timezones = (await frappe.call({
        method:'erpnext.www.book_appointment.index.get_timezones'
    })).message;
    window.holiday_list = window.appointment_settings.holiday_list;
}

function setup_timezone_selector() {
    let timezones_element = document.getElementById('appointment-timezone');
    let local_timezone = moment.tz.guess()
    window.timezones.forEach(timezone => {
        let opt = document.createElement('option');
        opt.value = timezone;
        if (timezone == local_timezone) {
            opt.selected = true;
        }
        opt.innerHTML = timezone;
        timezones_element.appendChild(opt)
    });
}

function setup_date_picker() {
    let date_picker = document.getElementById('appointment-date');
    let today = new Date();
    date_picker.min = today.toISOString().substr(0, 10);
    today.setDate(today.getDate() + window.appointment_settings.advance_booking_days);
    date_picker.max = today.toISOString().substr(0, 10);
}

function hide_next_button() {
    let next_button = document.getElementById('next-button');
    next_button.disabled = true;
    next_button.onclick = () => frappe.msgprint(__("Please select a date and time"));
}

function show_next_button() {
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
        frappe.throw(__('Please select a date'));
    }
    window.selected_date = date_picker.value;
    window.selected_timezone = timezone.value;
    update_time_slots(date_picker.value, timezone.value);
    let lead_text = document.getElementById('lead-text');
    lead_text.innerHTML = "Select Time"
}

async function get_time_slots(date, timezone) {
    let slots = (await frappe.call({
        method: 'erpnext.www.book_appointment.index.get_appointment_slots',
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
    window.slots.forEach((slot, index) => {
        // Get and append timeslot div
        let timeslot_div = get_timeslot_div_layout(slot)
        timeslot_container.appendChild(timeslot_div);
    });
    set_default_timeslot();
}

function get_timeslot_div_layout(timeslot) {
    let start_time = new Date(timeslot.time)
    let timeslot_div = document.createElement('div');
    timeslot_div.classList.add('time-slot');
    if (!timeslot.availability) {
        timeslot_div.classList.add('unavailable')
    }
    timeslot_div.innerHTML = get_slot_layout(start_time);
    timeslot_div.id = timeslot.time.substring(11, 19);
    timeslot_div.addEventListener('click', select_time);
    return timeslot_div
}

function clear_time_slots() {
    // Clear any existing divs in timeslot container
    let timeslot_container = document.getElementById('timeslot-container');
    while (timeslot_container.firstChild) {
        timeslot_container.removeChild(timeslot_container.firstChild);
    }
}

function get_slot_layout(time) {
    let timezone = document.getElementById("appointment-timezone").value;
    time = new Date(time);
    let start_time_string = moment(time).tz(timezone).format("LT");
    let end_time = moment(time).tz(timezone).add(window.appointment_settings.appointment_duration, 'minutes');
    let end_time_string = end_time.format("LT");
    return `<span style="font-size: 1.2em;">${start_time_string}</span><br><span class="text-muted small">to ${end_time_string}</span>`;
}

function select_time() {
    if (this.classList.contains('unavailable')) {
        return;
    }
    let selected_element = document.getElementsByClassName('selected');
    if (!(selected_element.length > 0)) {
        this.classList.add('selected');
        show_next_button();
        return;
    }
    selected_element = selected_element[0]
    window.selected_time = this.id;
    selected_element.classList.remove('selected');
    this.classList.add('selected');
    show_next_button();
}

function set_default_timeslot() {
    let timeslots = document.getElementsByClassName('time-slot')
    // Can't use a forEach here since, we need to break the loop after a timeslot is selected
    for (let i = 0; i < timeslots.length; i++) {
        const timeslot = timeslots[i];
        if (!timeslot.classList.contains('unavailable')) {
            timeslot.classList.add('selected');
            break;
        }
    }
}

function navigate_to_page(page_number) {
    let page1 = document.getElementById('select-date-time');
    let page2 = document.getElementById('enter-details');
    switch (page_number) {
        case 1:
            page1.style.display = 'block';
            page2.style.display = 'none';
            break;
        case 2:
            page1.style.display = 'none';
            page2.style.display = 'block';
            break;
        default:
            break;
    }
}

function setup_details_page() {
    navigate_to_page(2)
    let date_container = document.getElementsByClassName('date-span')[0];
    let time_container = document.getElementsByClassName('time-span')[0];
    setup_search_params();
    date_container.innerHTML = moment(window.selected_date).format("MMM Do YYYY");
    time_container.innerHTML = moment(window.selected_time, "HH:mm:ss").format("LT");
}

function setup_search_params() {
    let search_params = new URLSearchParams(window.location.search);
    let customer_name = search_params.get("name")
    let customer_email = search_params.get("email")
    let detail = search_params.get("details")
    if (customer_name) {
        let name_input = document.getElementById("customer_name");
        name_input.value = customer_name;
        name_input.disabled = true;
    }
    if(customer_email) {
        let email_input = document.getElementById("customer_email");
        email_input.value = customer_email;
        email_input.disabled = true;
    }
    if(detail) {
        let detail_input = document.getElementById("customer_notes");
        detail_input.value = detail;
        detail_input.disabled = true;
    }
}
async function submit() {
    let button = document.getElementById('submit-button');
    button.disabled = true;
    let form = document.querySelector('#customer-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        button.disabled = false;
        return;
    }
    let contact = get_form_data();
    let appointment =  frappe.call({
        method: 'erpnext.www.book_appointment.index.create_appointment',
        args: {
            'date': window.selected_date,
            'time': window.selected_time,
            'contact': contact,
            'tz':window.selected_timezone
        },
        callback: (response)=>{
            if (response.message.status == "Unverified") {
                frappe.show_alert("Please check your email to confirm the appointment")
            } else {
                frappe.show_alert("Appointment Created Successfully");
            }
            setTimeout(()=>{
                let redirect_url = "/";
                if (window.appointment_settings.success_redirect_url){
                    redirect_url += window.appointment_settings.success_redirect_url;
                }
                window.location.href = redirect_url;},5000)
        },
        error: (err)=>{
            frappe.show_alert("Something went wrong please try again");
            button.disabled = false;
        }
    });
}

function get_form_data() {
    contact = {};
    let inputs = ['name', 'skype', 'number', 'notes', 'email'];
    inputs.forEach((id) => contact[id] = document.getElementById(`customer_${id}`).value)
    return contact
}
