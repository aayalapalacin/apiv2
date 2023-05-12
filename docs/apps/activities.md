## Activity API

This API uses Google DataStore as storage, there is not local storage on Heroku or Postgres.

We need Google DataStore because we plan to store huge amounts of activities that the user can do inside breathecode.

Possible activities (so far):
```
"breathecode_login" //every time it logs in
"online_platform_registration" //first day using breathecode
"public_event_attendance" //attendy on an eventbrite event
"classroom_attendance" //when the student attent to class
"classroom_unattendance" //when the student miss class
"lesson_opened" //when a lessons is opened on the platform
"office_attendance" //when the office raspberry pi detects the student
"nps_survey_answered" //when a nps survey is answered by the student
"exercise_success" //when student successfully tests exercise
```

Any activity has the following inputs:

```
    'cohort',
    'data',
    'day',
    'slug',
    'user_agent',
```

## Endpoints for the user

Get recent user activity
```
GET: activity/user/{email_or_id}?slug=activity_slug
```

Add a new user activity (requires authentication)
```
POST: activity/user/{email_or_id}
{
    'slug' => 'activity_slug',
    'data' => 'any aditional data (string or json-encoded-string)'
}

💡 Node: You can pass the cohort in the data json object and it will be possible to filter on the activity graph like this:

{
    'slug' => 'activity_slug',
    'data' => "{ \"cohort\": \"mdc-iii\" }" (json encoded string with the cohort id)
}
```

Endpoints for the Cohort

Get recent user activity
```
GET: activity/cohort/{slug_or_id}?slug=activity_slug
```
Endpoints for the coding_error's
```
Get recent user coding_errors
GET: activity/coding_error/{email_or_id}?slug=activity_slug
```
```
Add a new coding_error (requires authentication)
POST: activity/coding_error/

{
    "user_id" => "my@email.com",
    "slug" => "webpack_error",
    "data" => "optional additional information about the error",
    "message" => "",
    "name" => "module-not-found,
    "severity" => "900",
    "details" => "stack trace for the error as string"
}
```
