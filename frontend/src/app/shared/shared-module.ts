import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MaterialModule } from './material.module';
import { AiSearchBar } from './components/ai-search-bar/ai-search-bar';
import { SafeUrlPipe } from './pipes/safe-url-pipe';
import { ConfirmationDialog } from './components/confirmation-dialog/confirmation-dialog';
import { ImageDialogComponent } from './components/image-dialog/image-dialog';

@NgModule({
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MaterialModule,
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
    MaterialModule,
  ],
})
export class SharedModule { }
