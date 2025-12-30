import { Routes } from '@angular/router';

export const MARKETING_ROUTES: Routes = [
    {
        path: '',
        loadComponent: () => import('./components/campaign-list/campaign-list.component')
            .then(m => m.CampaignListComponent)
    },
    {
        path: 'new',
        loadComponent: () => import('./components/campaign-wizard/campaign-wizard.component')
            .then(m => m.CampaignWizardComponent)
    },
    {
        path: 'calendar',
        loadComponent: () => import('./components/campaign-calendar/campaign-calendar.component')
            .then(m => m.CampaignCalendarComponent)
    },
    {
        path: 'connectors',
        loadComponent: () => import('./components/connector-settings/connector-settings.component')
            .then(m => m.ConnectorSettingsComponent)
    },
    {
        path: ':id/edit',
        loadComponent: () => import('./components/campaign-wizard/campaign-wizard.component')
            .then(m => m.CampaignWizardComponent)
    },
    {
        path: ':id',
        loadComponent: () => import('./components/campaign-detail/campaign-detail.component')
            .then(m => m.CampaignDetailComponent)
    },
];
