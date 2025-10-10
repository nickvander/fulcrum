import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { UserList } from './components/user-list/user-list';
import { UserForm } from './components/user-form/user-form';

const routes: Routes = [
  { path: '', component: UserList },
  { path: 'edit/:id', component: UserForm },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class UsersRoutingModule { }
