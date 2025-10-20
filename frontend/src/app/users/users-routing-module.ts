import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { UserList } from './components/user-list/user-list';
import { UserForm } from './components/user-form/user-form';
import { AccountManagement } from './components/account-management/account-management';
import { AdminGuard } from '../core/guards/admin.guard';

const routes: Routes = [
  { path: '', component: UserList, canActivate: [AdminGuard] },
  { path: 'create', component: UserForm, canActivate: [AdminGuard] },
  { path: 'edit/:id', component: UserForm, canActivate: [AdminGuard] },
  { path: 'account', component: AccountManagement }, // No guard for account management - users can access their own profile
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class UsersRoutingModule { }
