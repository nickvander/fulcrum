import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { Subject, takeUntil } from 'rxjs';
import { CustomField } from '../../models/custom-field.model';
import { CustomFieldService } from '../../services/custom-field.service';
import { CustomFieldDialog } from '../custom-field-dialog/custom-field-dialog';
import { ConfirmationDialog } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

@Component({
  selector: 'app-custom-field-list',
  templateUrl: './custom-field-list.html',
  styleUrls: ['./custom-field-list.scss'],
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule, MatIconModule],
})
export class CustomFieldList implements OnInit, OnDestroy {
  displayedColumns: string[] = ['name', 'type', 'actions'];
  customFields: CustomField[] = [];
  private destroy$ = new Subject<void>();

  constructor(
    private customFieldService: CustomFieldService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.customFieldService.customFields$
      .pipe(takeUntil(this.destroy$))
      .subscribe((fields) => {
        this.customFields = fields;
      });
    this.customFieldService.getCustomFields().subscribe();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  openCustomFieldDialog(field?: CustomField): void {
    const dialogRef = this.dialog.open(CustomFieldDialog, {
      data: field,
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        if (field) {
          this.customFieldService.updateCustomField({ ...field, ...result }).subscribe();
        } else {
          this.customFieldService.createCustomField(result).subscribe();
        }
      }
    });
  }

  deleteCustomField(id: number): void {
    const dialogRef = this.dialog.open(ConfirmationDialog, {
      data: {
        title: 'Delete Custom Field',
        message: 'Are you sure you want to delete this custom field? This action cannot be undone.',
      },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.customFieldService.deleteCustomField(id).subscribe();
      }
    });
  }
}
