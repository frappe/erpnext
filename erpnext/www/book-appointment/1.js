
let holidays = [];
{% if holidays %}
    holidays = {{holidays}}
{% endif %}

function next() {
    let date = document.getElementsByName('appointment-date')[0].value;
    if(holidays.includes(date)){
        frappe.throw("That day is a holiday")
    }
    let tz = document.getElementsByName('appointment-timezone')[0].value;
    window.location = `/book-appointment/2?date=${date}&tz=${tz}`;
}