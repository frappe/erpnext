# Lab Test

ERPNext Healthcare allows you to manage a clinical laboratory efficiently by allowing you to enter Lab Tests and print or email test results, manage samples collected, create Invoice etc. ERPNext Healthcare comes pre-packed with some sample tests, you can reconfigure Lab Test Templates for each Test and its result format or crate new ones. You can do this in
>Healthcare > Setup > Lab Text Templates

Once you have all necessary Lab Test Templates configured, you can start creating Lab Tests by selecting a Test Template every time you create a Test. To create a new Lab Test
>Healthcare > Laboratory > Lab Test > New Lab Test

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/lab_test_1.png">

You can record the test results in the Lab Test document as the results gets ready.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/lab_test_2.png">

> Note: To create Sample Collection documents for every Lab Test, check "Manage Sample Collection" flag in Healthcare Settings and select Sample in the Lab Test Template

In many Laboratories, approval of Lab Tests is a must before printing and submitting the document. ERPNext Healthcare allows you to create Users with Role "Lab Test Approver" for this. You will also have to enable this in
>Healthcare Settings > Laboratory Settings > Require Lab Test Approval

This will ensure that emailing or printing of Lab Tests can only be done after Approval of the Lab Test by the Lab Test Approver.

{next}
