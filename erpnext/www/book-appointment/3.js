function submit(){
    let params = new URLSearchParams(window.location.search);
    const date = params.get('date');
    const time = params.get('time');
    const tz = params.get('tz');
    const customer_name = document.getElementById('customer_name').value;
    const customer_number = document.getElementById('customer_number').value;
    const customer_skype = document.getElementById('customer_skype').value;
    const customer_notes = document.getElementById('customer_notes').value;
    console.log({date,time,tz,customer_name,customer_number,customer_skype,customer_notes});
}