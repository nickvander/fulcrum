import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MarketplaceListComponent } from './pages/marketplace-list/marketplace-list';
import { MarketplaceDetailComponent } from './pages/marketplace-detail/marketplace-detail';
import { MarketplaceSettingsComponent } from './pages/marketplace-settings/marketplace-settings';

import { MarketplaceCallbackComponent } from './pages/marketplace-callback/marketplace-callback';

const routes: Routes = [
  { path: '', component: MarketplaceListComponent },
  { path: 'settings/:type', component: MarketplaceSettingsComponent },
  { path: ':type/callback', component: MarketplaceCallbackComponent },
  { path: ':id', component: MarketplaceDetailComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class MarketplacesRoutingModule { }
