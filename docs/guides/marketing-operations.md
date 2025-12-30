# Marketing Operations Guide

The Marketing module in Fulcrum allows you to manage campaigns, schedule events
(posts, emails), and track performance across multiple channels from a central
dashboard.

## System Components

- **Campaigns**: Group your marketing efforts by goal, budget, and time.
- **Events**: Individual posts, emails, or ads.
- **Connectors**: Bridges to external platforms (SMTP for email, Instagram API,
  etc.).
- **Calendar**: Visual scheduling and drag-and-drop management.

## Technical Implementation

### Backend

The backend is built with FastAPI and SQLAlchemy.

- **Models**: Located in `src/models/marketing.py`.
- **CRUD**: Generic and model-specific logic in `src/crud/crud_marketing.py`.
- **API**: Centralized routing in `src/api/v1/endpoints/marketing.py`.

### Frontend

- **MarketingService**: Handles all API calls including file uploads for content
  images.
- **Date Filtering**: Uses a shared `DateRangePresetsComponent` with custom
  logic to handle future-dated campaigns.
- **FullCalendar**: Integrated using `@fullcalendar/angular`.
- **Shared UI**: Utilizes `StatusFilterComponent` and `SleekSelect` for a modern
  look.

## Development Guide

### Adding a New Connector Type

1. Add the type to `ConnectorType` enum in `src/models/marketing.py`.
2. Implement a new class inheriting from `MarketingConnectorBase` in
   `src/services/marketing/`.
3. Update the factory method to return your new connector based on the type.

### UI Customization

Marketing styles are scoped to components but utilize global variables from
`styles.scss`.

- Use the `marketing-dialog-panel` class when opening dialogs to ensure
  full-width headers.
- KPIs are managed via `CampaignListComponent.calculateKPIs()`.

## Best Practices for Developers

- **Database Consistency**: Always ensure that `CampaignEvent` records are
  updated when a parent `Campaign` dates change.
- **Responsive Design**: The marketing dashboard uses CSS Grid and Flexbox to
  remain functional on mobile and desktop.
- **Error Handling**: Marketing connectors should gracefully handle API failures
  and log them to `EventAnalytics` for user visibility.
