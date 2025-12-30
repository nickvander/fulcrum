# Bulk User Import

The Bulk User Import feature allows administrators to onboard multiple users
simultaneously by uploading a CSV file.

## Prerequisites

- You must be logged in as an **Administrator**.
- You need a CSV file prepared with the user data.

## CSV Format

The CSV file must contain the following headers:

- `email` (Required): The user's email address.
- `first_name` (Required): The user's first name.
- `last_name` (Required): The user's last name.
- `user_type` (Optional): One of `admin`, `employee`, or `customer`. Defaults to
  `employee` if omitted.

### Example CSV Content

```csv
email,first_name,last_name,user_type
john.doe@example.com,John,Doe,employee
jane.smith@example.com,Jane,Smith,admin
customer1@example.com,Customer,One,customer
```

## How to Import Users

1.  Navigate to the **Users** page.
2.  Click the **Import Users** button in the top action bar.
3.  (Optional) Click **Download Template** to get a sample CSV file.
4.  Click **Choose File** and select your prepared CSV file.
5.  Click **Import**.

## Results

After the import is processed, a summary will be displayed:

- **Created Users**: A list of successfully created users.
  - **Important**: The system generates a secure random password for each new
    user. These passwords are displayed in the results table. **Copy these
    passwords immediately** and distribute them to the users, as they will not
    be shown again.
- **Failed Rows**: A list of rows that could not be processed, along with the
  error reason (e.g., "User with this email already exists").
