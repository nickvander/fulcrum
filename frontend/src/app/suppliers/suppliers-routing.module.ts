import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SupplierListComponent } from './supplier-list/supplier-list.component';
import { SupplierDetailComponent } from './supplier-detail/supplier-detail.component';
import { PurchaseOrderListComponent } from './purchase-orders/purchase-order-list/purchase-order-list.component';
import { PurchaseOrderEditComponent } from './purchase-orders/purchase-order-edit/purchase-order-edit.component';

const routes: Routes = [
  // Supplier routes
  { path: '', component: SupplierListComponent },  // Supplier list
  { path: 'id/new', component: SupplierDetailComponent },
  { path: 'id/:id', component: SupplierDetailComponent },
  // Purchase Order routes
  { path: 'po', component: PurchaseOrderListComponent },
  { path: 'po/create', component: PurchaseOrderEditComponent },
  { path: 'po/:id', component: PurchaseOrderEditComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class SuppliersRoutingModule { }


