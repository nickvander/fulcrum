import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Header } from './components/header/header';
import { Sidenav } from './components/sidenav/sidenav';

const MATERIAL_MODULES = [
  MatToolbarModule,
  MatSidenavModule,
  MatListModule,
  MatIconModule,
  MatButtonModule,
];

@NgModule({
  declarations: [],
  imports: [
    Header,
    Sidenav,
    CommonModule,
    RouterModule,
    ...MATERIAL_MODULES
  ],
  exports: [
    Header,
    Sidenav,
    ...MATERIAL_MODULES
  ]
})
export class CoreModule { }
