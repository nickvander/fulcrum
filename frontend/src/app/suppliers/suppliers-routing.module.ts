import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SupplierDetailComponent } from './supplier-detail/supplier-detail.component';
import { PurchaseOrderListComponent } from './purchase-orders/purchase-order-list/purchase-order-list.component';
import { PurchaseOrderEditComponent } from './purchase-orders/purchase-order-edit/purchase-order-edit.component';

const routes: Routes = [
  { path: '', redirectTo: 'list', pathMatch: 'full' },
  { path: 'list', component: PurchaseOrderListComponent }, // Placeholder: should be Supplier List, but using PO list as main entry for now or create a Supplier List later.
  { path: 'id/:id', component: SupplierDetailComponent },
  { path: 'po/list', component: PurchaseOrderListComponent },
  { path: 'po/create', component: PurchaseOrderEditComponent },
  { path: 'po/:id', component: PurchaseOrderEditComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class SuppliersRoutingModule { }
