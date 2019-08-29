let time_slot_divs = document.getElementsByClassName('time-slot');

function get_available_slots() {
    frappe.db
}

function select_time() {
    if (this.classList.contains("unavailable")) {
        return
    }
    console.log(this.id)
    try{
        selected_element = document.getElementsByClassName('selected')[0]
    }catch(e){
        this.classList.add('selected')
    }
    selected_element.classList.remove('selected');
    this.classList.add('selected');
}

for (var i = 0; i < time_slot_divs.length; i++) {
    time_slot_divs[i].addEventListener('click', select_time);
}

function next() {
    let urlParams = new URLSearchParams(window.location.search);
    let date = urlParams.get("date");
    let tz = urlParams.get("tz");
    let time_slot = document.querySelector(".selected").id;
    window.location.href = `/book-appointment/3?date=${date}&tz=${tz}&time=${time_slot}`;
}