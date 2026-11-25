# Practice App – Requirements

## R1 – Page title
The home page title must be "Playwright Practice Page" and the main heading must show the same text.

## R2 – Add user: required fields
To add a user, Name, City and Role are required. If any of them is missing, the form must show an error and no user is created.

## R3 – Add user: experience
The user must choose an experience level: Junior or Senior. The selected experience must be saved together with the user.

## R4 – Add user: terms
The "I accept the terms" checkbox must be ticked before submitting. If it is not ticked, the message "Please accept the terms." is shown and no user is created.

## R5 – Add user: roles
Allowed roles are QA Engineer, Developer and Manager. No other role may be selected.

## R6 – Add user: success
After a successful submit, the message 'User "<name>" added successfully!' is shown, the form is cleared, and the new user appears in the users table.

## R7 – Users table
The users table shows ID, Name, City and Role for every user, plus a Delete button per row. The "Total users" counter must always equal the number of rows.

## R8 – Delete user
Clicking Delete removes that user from the table immediately and the total users counter decreases by 1.

## R9 – Alerts
"Show Alert" shows "Hello! This is an alert.". "Show Confirm" asks "Do you want to continue?" and shows "You clicked OK." or "You clicked Cancel.". "Show Prompt" asks for a name and greets the user with "Hello, <name>!".

## R10 – Delayed message
Clicking "Load Message (3 seconds)" first shows "Loading..." and after about 3 seconds shows "Data loaded after 3 seconds!".

## R11 – Links
The internal link opens the frame page. The external link opens playwright.dev in a new tab. The broken link is intentional and must return a 404 page.

## R12 – iFrame
The iFrame contains an input and a button. Clicking the button shows "Frame says: <text>" with the typed text, or "(empty)" if nothing was typed.
