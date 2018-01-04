<h1>Leave Calculation In Salary Slip</h1>

There are two types of leave which user can apply for.
<br>
<br>
<ol>
    <li>Paid Leave (Sick Leave, Privilege Leave, Casual Leave etc.)</li>
    <li>Unpaid Leave
        <br>
    </li>
</ol>Paid Leave are firstly allocated by HR manager. As and when Employee creates Leave Application, leaves allocated to him/her are deducted. These leaves doesn't have impact on the employee's Salary Slip.
<br>
<br>When Employee is out of paid leave, he create Leave Application for unpaid leave. The term used for unpaid leave in ERPNext is Leave Without Pay (LWP). These leaves does have impact on the Employee's Salary Slip.
<br>
<br>
<div class="well">Just marking Absent in the Attendance record do not have impact on salary calculation of an Employee, as that absenteeism could be because of paid leave. Hence creating Leave Application should be created incase of absenteeism.<br></div>Let's consider
a scenario to understand how leaves impact employees Salary Slip.
<br>
<br><b>Masters:</b>

<br>
<br>
<ol>
    <li>Setup Employee</li>
    <li>Allocate him paid leaves</li>
    <li>Create Salary Structure for that Employee. In the Earning and Deduction table, select which component of salary should be affected if Employee takes LWP.</li>
    <li>Create Holiday List (if any), and link it with Employee master.</li>
</ol>
<p>When creating Salary Slip for an Employee, following is what you will see:</p>
<img src="/docs/assets/img/articles/SGrab_282.png">
<br>
<br><b>Working Days:</b> Working Days in Salary Slip are calculated based on number of days selected above. If you don't wish to consider holiday in Working Days, then you should do following setting.
<br>
<br>
<div class="well">Human Resource &gt;&gt; Setup &gt;&gt; HR Setting
    <br>
    <br>Uncheck field "Include Holidays in Total No. of Working Days"
    <br>
</div>Holidays are counted based on Holiday List attached to the Employee's master.<b><br><br>Leave Without Pay: </b>Leave Without Pay is updated based on Leave Application made for this Employee, in the month for which Salary Slip is created, and which has
Leave Type as "Leave Without Pay".
<br>
<br><b>Payment Days:</b> Following is how Payment Days are calculated:
<br>
<br>Payment Days = Working Days - Leave Without Pay
<br>
<br>As indicated above, if you have LWP checked for components in the earning and deducted table, you will notice a reduction in Amount based on no. of LWP of an Employee for that month.
<br>
<br>
<img src="/docs/assets/img/articles/SGrab_283.png" width="760"><br>


<!-- markdown -->