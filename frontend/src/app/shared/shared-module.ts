import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule } from '@angular/material/dialog';
import { AiSearchBar } from './components/ai-search-bar/ai-search-bar';
import { SafeUrlPipe } from './pipes/safe-url-pipe';
import { ConfirmationDialog } from './components/confirmation-dialog/confirmation-dialog';
import { ImageDialogComponent } from './components/image-dialog/image-dialog';

const MATERIAL_MODULES = [
  MatFormFieldModule,
  MatInputModule,
  MatButtonModule,
  MatIconModule,
  MatDialogModule
];

@NgModule({
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ...MATERIAL_MODULES,
    AiSearchBar, // Import standalone components
    SafeUrlPipe, // Import standalone pipes
    ConfirmationDialog,
    ImageDialogComponent,
  ],
  exports: [
    AiSearchBar, // Re-export standalone components
    SafeUrlPipe, // Re-export standalone pipes
    ConfirmationDialog,
    ImageDialogComponent,
    CommonModule,
    ReactiveFormsModule,
    ...MATERIAL_MODULES,
  ],
})
export class SharedModule {}
