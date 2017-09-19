# Patient Appointment
ERPNext Healthcare allows you to book Patient appointments for any date and if configured, send them alerts via Email or SMS.

You can create a Patient Appointment from
> Healthcare > Patient Appointment > New Patient Appointment

You can book appointments for a registered Patient by searching and selecting the Patient field. You can search the Patient by Patient ID, Name, Email or Mobile number. You can also register a new Patient from the Appointment screen by selecting "Create a new patient" in the Patient field.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/appointment_1.png">

If you have a front desk executive to manage your appointments, you can configure a user role to have access to Patient Appointment so that she can do the bookings by selecting the Physician whom the Patient wish to consult and the date for booking. "Check Availability" button will pop up all the available time slots with status indicators for the date. She can select a time slot and "Book" the Appointment for the Patient.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/appointment_2.png">

After Booking, the scheduled time of the Appointment and duration will be updated and seved in the document.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/appointment_3.png">

You can configure ERPNext to send an SMS alert to the Patient about the booking confirmation or a reminder on the day of Appointment by doing necessary configurations in -

> Healthcare > Healthcare Settings > Out Patient SMS Alerts

The screen also allows the executive to select a Referring Physician so that you can track the source the appointment.

### Actions
  * Billing: If you collect the consultation fee while booking the Appointment itself you can do so by using the "Create > Invoice" button. This will take you to the ERPNext Accounts Sales Invoice screen.

  * Vital Signs: "Create > Vital Signs" button will take you to the new Vital Signs screen to record the vitals of the Patient.

  * Consultation: From the Appointment screen you can directly create a Consultation to record the details of patient encounter.

  * View Patient Medical Record.

> Note: User should have privileges (User Role) to view the buttons

A Patient can also book an appointment with a Physician by checking the Physician's availability directly through the **ERPNext Portal**.

{next}
