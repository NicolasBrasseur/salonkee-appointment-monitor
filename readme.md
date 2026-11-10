# Salonkee Appointment Availability Monitor

A lightweight Python automation tool that monitors appointment availability on Salonkee and sends Discord notifications whenever new time slots become available.

## The Problem

My hairdresser was fully booked, with new appointments being released gradually. However, newly available slots were often booked by other customers very quickly.

I had to manually check the Salonkee application every day to see whether new appointments had become available. This was repetitive and time-consuming, especially since there was no notification system for newly released appointments.

I decided to build a small monitoring tool to automate this process.

The script runs every two hours using Windows Task Scheduler, checks appointment availability, detects changes, and sends notifications to a dedicated Discord channel.

## How It Works

The application follows a simple monitoring cycle:

1. **Fetch availability** – Sends an HTTP POST request to Salonkee's availability endpoint to retrieve available appointment slots over a rolling date range, from today until one month ahead.
2. **Parse the response** – Extracts appointment dates, start times, and end times from the JSON response.
3. **Compare availability** – Compares the current results with the previously saved state to identify newly available and no longer available slots.
4. **Notify via Discord** – Sends a notification when availability changes, including a summary of all currently available appointments.
5. **Persist the state** – Saves the latest availability and the date of the last daily summary in a local JSON file.

## Technical Investigation

One of the main challenges was understanding how Salonkee retrieves and exposes appointment availability.

Rather than relying on manual checks or attempting to interact with the application's user interface, I investigated the network requests made by the Salonkee website.

### 1. Inspecting Network Requests

I used the browser's developer tools, particularly the Network tab, while navigating through the appointment booking process.

By observing the HTTP requests triggered when selecting a service and checking available dates, I identified the endpoint responsible for retrieving appointment availability.

I then inspected the request details:

- HTTP method and endpoint URL.
- Request headers.
- JSON payload and its parameters.
- Response status and response structure.

### 2. Understanding the API Payload

Once the relevant request was identified, I examined the parameters required to reproduce it.

This included the salon identifier, service identifiers, booking configuration, and requested date range.

I also inspected the JSON response to understand how available time slots were organized by date and how their start and end times were represented.

### 3. Reproducing the Request in Python

After understanding the request structure, I reproduced it using Python's `requests` library.

I tested different date ranges and verified that the returned data matched the availability displayed on the website.

This allowed me to move from inspecting the website manually to querying the underlying availability endpoint directly.

### 4. Implementing the Monitoring Logic

With the request and response structures understood, I implemented the extraction, comparison, persistence, and notification logic.

I used a local JSON file to retain the previous state between executions, allowing the application to detect changes even though each scheduled run starts a new Python process.

## Technologies Used

- **Python** – Main application logic.
- **Requests** – HTTP requests to the Salonkee availability endpoint and Discord webhook.
- **JSON** – Parsing API responses and persisting availability between executions.
- **Python Dateutil** – Dynamic date range calculation using `relativedelta`.
- **Discord Webhooks** – Sending automated notifications to a dedicated Discord channel.
- **Windows Task Scheduler** – Running the script automatically every two hours.


## Key Takeaways

This project was a practical exercise in:

- Reverse-engineering network interactions through browser developer tools.
- Understanding and reproducing HTTP requests to an existing API.
- Working with JSON data and external services.
- Implementing state persistence between independent executions.
- Detecting changes through set comparisons.
- Automating recurring tasks and integrating Discord notifications.

The project started as a small personal convenience tool and provided an opportunity to investigate an existing web application's network communication and turn that investigation into a working Python automation.

The application isn't meant to be used by someone other than me but I decided to post it here on Github to show my thought process and how I can handle and solve real life problems by creating small applications like this one.