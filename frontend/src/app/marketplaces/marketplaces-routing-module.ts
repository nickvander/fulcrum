import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MarketplaceListComponent } from './pages/marketplace-list/marketplace-list';
import { MarketplaceDetailComponent } from './pages/marketplace-detail/marketplace-detail';

const routes: Routes = [
  { path: '', component: MarketplaceListComponent },
  { path: ':id', component: MarketplaceDetailComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class MarketplacesRoutingModule { }
