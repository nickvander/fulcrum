import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Login } from './auth/components/login/login';
import { AuthGuard } from './auth/guards/auth-guard';
import { LoginGuard } from './auth/guards/login-guard';

const routes: Routes = [
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
  { path: '', redirectTo: '/products', pathMatch: 'full' },
  {
    path: 'ingest',
    loadComponent: () =>
      import('./products/product-ingestion/product-ingestion').then(
        (m) => m.ProductIngestion
      ),
  },
  { path: 'users', loadChildren: () => import('./users/users-module').then(m => m.UsersModule) },
  { path: '**', redirectTo: '/products' } // Wildcard route
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
