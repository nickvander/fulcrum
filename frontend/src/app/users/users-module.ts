import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';

import { UsersRoutingModule } from './users-routing-module';
import { UserList } from './components/user-list/user-list';
import { UserForm } from './components/user-form/user-form';
import { AccountManagement } from './components/account-management/account-management';
import { PasswordResetDialog } from './components/password-reset-dialog/password-reset-dialog';
import { ConfirmationDialog } from './components/confirmation-dialog/confirmation-dialog';
import { UserService } from './services/user.service';


@NgModule({
  imports: [
    CommonModule,
    ReactiveFormsModule,
    UsersRoutingModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSlideToggleModule,
    MatSelectModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDialogModule,
    UserList,
    UserForm,
    AccountManagement,
    PasswordResetDialog,
    ConfirmationDialog
  ],
  providers: [
    UserService
  ]
})
export class UsersModule { }
