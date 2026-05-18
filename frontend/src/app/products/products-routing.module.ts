import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ProductList } from './components/product-list/product-list';
import { ProductForm } from './components/product-form/product-form';

const routes: Routes = [
  { path: 'dashboard', loadComponent: () => import('./pages/product-dashboard/product-dashboard.component').then(m => m.ProductDashboardComponent) },
  {
    path: 'audit',
    loadComponent: () => import('./pages/inventory-audit/inventory-audit.component').then(m => m.InventoryAuditComponent),
  },
  { path: '', component: ProductList },
  { path: 'new', component: ProductForm },
  { path: 'edit/:id', component: ProductForm }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProductsRoutingModule { }
