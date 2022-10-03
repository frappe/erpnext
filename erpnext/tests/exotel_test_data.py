import frappe

call_initiation_data = frappe._dict(
	{
		"CallSid": "23c162077629863c1a2d7f29263a162m",
		"CallFrom": "09999999991",
		"CallTo": "09999999980",
		"Direction": "incoming",
		"Created": "Wed, 23 Feb 2022 12:31:59",
		"From": "09999999991",
		"To": "09999999988",
		"CurrentTime": "2022-02-23 12:32:02",
		"DialWhomNumber": "09999999999",
		"Status": "busy",
		"EventType": "Dial",
		"AgentEmail": "test_employee_exotel@company.com",
	}
)

call_end_data = frappe._dict(
	{
		"CallSid": "23c162077629863c1a2d7f29263a162m",
		"CallFrom": "09999999991",
		"CallTo": "09999999980",
		"Direction": "incoming",
		"ForwardedFrom": "null",
		"Created": "Wed, 23 Feb 2022 12:31:59",
		"DialCallDuration": "17",
		"RecordingUrl": "https://s3-ap-southeast-1.amazonaws.com/random.mp3",
		"StartTime": "2022-02-23 12:31:58",
		"EndTime": "1970-01-01 05:30:00",
		"DialCallStatus": "completed",
		"CallType": "completed",
		"DialWhomNumber": "09999999999",
		"ProcessStatus": "null",
		"flow_id": "228040",
		"tenant_id": "67291",
		"From": "09999999991",
		"To": "09999999988",
		"RecordingAvailableBy": "Wed, 23 Feb 2022 12:37:25",
		"CurrentTime": "2022-02-23 12:32:25",
		"OutgoingPhoneNumber": "09999999988",
		"Legs": [
			{
				"Number": "09999999999",
				"Type": "single",
				"OnCallDuration": "10",
				"CallerId": "09999999980",
				"CauseCode": "NORMAL_CLEARING",
				"Cause": "16",
			}
		],
	}
)

call_disconnected_data = frappe._dict(
	{
		"CallSid": "d96421addce69e24bdc7ce5880d1162l",
		"CallFrom": "09999999991",
		"CallTo": "09999999980",
		"Direction": "incoming",
		"ForwardedFrom": "null",
		"Created": "Mon, 21 Feb 2022 15:58:12",
		"DialCallDuration": "0",
		"StartTime": "2022-02-21 15:58:12",
		"EndTime": "1970-01-01 05:30:00",
		"DialCallStatus": "canceled",
		"CallType": "client-hangup",
		"DialWhomNumber": "09999999999",
		"ProcessStatus": "null",
		"flow_id": "228040",
		"tenant_id": "67291",
		"From": "09999999991",
		"To": "09999999988",
		"CurrentTime": "2022-02-21 15:58:47",
		"OutgoingPhoneNumber": "09999999988",
		"Legs": [
			{
				"Number": "09999999999",
				"Type": "single",
				"OnCallDuration": "0",
				"CallerId": "09999999980",
				"CauseCode": "RING_TIMEOUT",
				"Cause": "1003",
			}
		],
	}
)

call_not_answered_data = frappe._dict(
	{
		"CallSid": "fdb67a2b4b2d057b610a52ef43f81622",
		"CallFrom": "09999999991",
		"CallTo": "09999999980",
		"Direction": "incoming",
		"ForwardedFrom": "null",
		"Created": "Mon, 21 Feb 2022 15:47:02",
		"DialCallDuration": "0",
		"StartTime": "2022-02-21 15:47:02",
		"EndTime": "1970-01-01 05:30:00",
		"DialCallStatus": "no-answer",
		"CallType": "incomplete",
		"DialWhomNumber": "09999999999",
		"ProcessStatus": "null",
		"flow_id": "228040",
		"tenant_id": "67291",
		"From": "09999999991",
		"To": "09999999988",
		"CurrentTime": "2022-02-21 15:47:40",
		"OutgoingPhoneNumber": "09999999988",
		"Legs": [
			{
				"Number": "09999999999",
				"Type": "single",
				"OnCallDuration": "0",
				"CallerId": "09999999980",
				"CauseCode": "RING_TIMEOUT",
				"Cause": "1003",
			}
		],
	}
)
