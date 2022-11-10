console.log('Loaded ESCO JS');

let empty = (data) => {
    data = ((typeof data === 'object') && data != null) ? (data.length) : ((data === 'undefined') ? undefined : data); 
    let toCheck = ["", null, undefined, "undefined", 0];
    return (toCheck.indexOf(data) >= 0);
}

let style = `
    .navbar{
        background: #2490ef !important;
    }
`;

let content = $("head style").append(style);
let loggedTime = localStorage.getItem('loggedTime');
loggedTime = (empty(loggedTime)) ? Date.now() : Number(loggedTime);
localStorage.current_workspace = "ESCO";

let redirectUser = () => {
    let isLoaded = $('script').load();
    let now = Date.now();
    let role = frappe.user_roles;

    let diff = (now - loggedTime)/1000;

    let recursion = setTimeout( () => {
        redirectUser();
    }, 100)
    
    if(isLoaded.length && !empty(role)){
        let url = window.location.href;

        clearTimeout(recursion);


        if(diff <= 10){
            localStorage.setItem('loggedTime', now);
        }

        // checks user's role and last login time. if it is less than 5 seconds, the system will redirect you.
        if((role[0] === 'Plant Manager')){
            $('form[role="search"]').hide();
            if(empty(url.match(/\/Production(.*)Table/gi)) && (diff <= 5)){
                window.location = '/app/query-report/Production%20Table';
            } 
        }
        else if((role[0] === 'Production Manager')){
            $('form[role="search"]').hide();
            if(empty(url.match(/work-order/gi)) && (diff <= 5)){
                window.location = '/app/work-order';
            }
        }
        else if((role[0] === 'Operator')){
            $('form[role="search"]').hide();
            if(empty(url.match(/\/Job(.*)Cards/gi))){
                window.location = '/app/query-report/Job%20Cards';
            }
        }
    
        $("header.navbar a[href='/app']").attr({"href":"/"});
    }
}

redirectUser();
