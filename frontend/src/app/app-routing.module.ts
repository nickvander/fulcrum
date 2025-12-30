import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Login } from './auth/components/login/login';
import { AuthGuard } from './auth/guards/auth-guard';
import { LoginGuard } from './auth/guards/login-guard';

const routes: Routes = [
  {
    path: 'dashboard',
    loadChildren: () => import('./dashboard/dashboard.module').then(m => m.DashboardModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'marketplaces',
    loadChildren: () => import('./marketplaces/marketplaces-module').then(m => m.MarketplacesModule),
    canActivate: [AuthGuard]
  },
  { path: 'login', component: Login, canActivate: [LoginGuard] },
  {
    path: 'forgot-password',
    loadComponent: () => import('./auth/components/forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent)
  },
  {
    path: 'reset-password',
    loadComponent: () => import('./auth/components/reset-password/reset-password.component').then(m => m.ResetPasswordComponent)
  },
  {
    path: 'products',
    loadChildren: () => import('./products/products-module').then(m => m.ProductsModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'settings',
    loadChildren: () => import('./settings/settings-module').then(m => m.SettingsModule),
    canActivate: [AuthGuard]
  },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'ingest',
    loadComponent: () =>
      import('./products/product-ingestion/product-ingestion').then(
        (m) => m.ProductIngestion
      ),
  },
  { path: 'users', loadChildren: () => import('./users/users-module').then(m => m.UsersModule) },
  {
    path: 'expenses',
    loadComponent: () => import('./expenses/components/expense-list/expense-list').then(m => m.ExpenseListComponent),
    canActivate: [AuthGuard]
  },
  { path: 'suppliers', loadChildren: () => import('./suppliers/suppliers.module').then(m => m.SuppliersModule), canActivate: [AuthGuard] },
  {
    path: 'marketing',
    loadChildren: () => import('./marketing/marketing.routes').then(m => m.MARKETING_ROUTES),
    canActivate: [AuthGuard]
  },
  { path: 'marketplaces', loadChildren: () => import('./marketplaces/marketplaces-module').then(m => m.MarketplacesModule), canActivate: [AuthGuard] },

  { path: '**', redirectTo: '/products' } // Wildcard route
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
