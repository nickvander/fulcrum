import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AiSearchBar } from './components/ai-search-bar/ai-search-bar';
import { SafeUrlPipe } from './pipes/safe-url-pipe';

const MATERIAL_MODULES = [
  MatFormFieldModule,
  MatInputModule,
  MatButtonModule,
  MatIconModule
];

@NgModule({
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ...MATERIAL_MODULES
  ],
  declarations: [AiSearchBar, SafeUrlPipe],
  exports: [
    AiSearchBar,
    SafeUrlPipe,
    CommonModule,
    ReactiveFormsModule,
    ...MATERIAL_MODULES
  ]
})
export class SharedModule { }
