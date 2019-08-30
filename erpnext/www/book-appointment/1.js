
{% include 'erpnext/public/js/date_polyfill.js' %}
let holidays = [];
{% if holidays %}
    holidays = {{holidays}}
{% endif %}

function next() {
    let date = document.getElementsByName('appointment-date')[0].value;
    if(holidays.includes(date)){
        frappe.throw("That day is a holiday")
    }
    if(date === ""){
        frappe.throw("Please select a date")
    }
    let tz = document.getElementsByName('appointment-timezone')[0].value;
    window.location = `/book-appointment/2?date=${date}&tz=${tz}`;
}

function ondatechange(){
    let date = document.getElementById('appointment-date')
    if(holidays.includes(date.value)){
        frappe.throw("That day is a holiday")
    }
}