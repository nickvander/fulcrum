import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PurchasingComponent } from './purchasing.component';
// Import your components here once they are created
// import { SupplierListComponent } from './suppliers/supplier-list/supplier-list.component';
// import { PurchaseOrderListComponent } from './purchase-orders/purchase-order-list/purchase-order-list.component';

const routes: Routes = [
  {
    path: '',
    component: PurchasingComponent,
    children: [
      // { path: 'suppliers', component: SupplierListComponent },
      // { path: 'purchase-orders', component: PurchaseOrderListComponent },
      { path: '', redirectTo: 'suppliers', pathMatch: 'full' },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class PurchasingRoutingModule {}
