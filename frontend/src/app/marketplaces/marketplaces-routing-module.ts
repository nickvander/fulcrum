import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MarketplaceListComponent } from './pages/marketplace-list/marketplace-list';
import { MarketplaceDetailComponent } from './pages/marketplace-detail/marketplace-detail';
import { MarketplaceSettingsComponent } from './pages/marketplace-settings/marketplace-settings';

import { MarketplaceCallbackComponent } from './pages/marketplace-callback/marketplace-callback';
import { MarketplaceHealthPageComponent } from './marketplace-health/marketplace-health-page.component';
import { StockTransferListComponent } from './stock-transfers/stock-transfer-list/stock-transfer-list';
import { StockTransferDetailComponent } from './stock-transfers/stock-transfer-detail/stock-transfer-detail';
import { StockTransferPlannerComponent } from './stock-transfers/stock-transfer-planner/stock-transfer-planner';
import { StockTransferReconciliationComponent } from './stock-transfers/stock-transfer-reconciliation/stock-transfer-reconciliation';

const routes: Routes = [
  { path: '', component: MarketplaceListComponent },
  { path: 'health', component: MarketplaceHealthPageComponent },
  { path: 'transfers', component: StockTransferListComponent },
  { path: 'transfers/planner', component: StockTransferPlannerComponent },
  { path: 'transfers/reconciliation', component: StockTransferReconciliationComponent },
  { path: 'transfers/:id', component: StockTransferDetailComponent },
  { path: 'settings/:type', component: MarketplaceSettingsComponent },
  { path: ':type/callback', component: MarketplaceCallbackComponent },
  { path: ':id', component: MarketplaceDetailComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class MarketplacesRoutingModule { }
