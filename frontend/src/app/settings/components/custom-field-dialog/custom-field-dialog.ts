import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { CustomField, FieldType } from '../../models/custom-field.model';

@Component({
  selector: 'app-custom-field-dialog',
  templateUrl: './custom-field-dialog.html',
  styleUrls: ['./custom-field-dialog.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
  ],
})
export class CustomFieldDialog {
  form: FormGroup;
  fieldTypes = Object.values(FieldType);

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<CustomFieldDialog>,
    @Inject(MAT_DIALOG_DATA) public data: CustomField
  ) {
    this.form = this.fb.group({
      name: [data?.name || '', Validators.required],
      type: [data?.type || FieldType.TEXT, Validators.required],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
