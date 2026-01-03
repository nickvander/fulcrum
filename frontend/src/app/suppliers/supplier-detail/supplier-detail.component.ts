import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { SuppliersService } from '../suppliers.service';
import { Supplier, SupplierCreate } from '../../shared/models/supplier.model';
import { SupplierProductManagerComponent } from '../supplier-product-manager/supplier-product-manager.component';

import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-supplier-detail',
  templateUrl: './supplier-detail.component.html',
  styleUrls: ['./supplier-detail.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterModule,
    MatTabsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    SupplierProductManagerComponent,
    TranslocoModule,
    MatSnackBarModule
  ]
})
export class SupplierDetailComponent implements OnInit {
  supplierForm: FormGroup;
  isEditMode = false;
  supplierId: number | null = null;

  constructor(
    private fb: FormBuilder,
    private suppliersService: SuppliersService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private translocoService: TranslocoService
  ) {
    this.supplierForm = this.fb.group({
      name: ['', Validators.required],
      contact_person: [''],
      email: ['', [Validators.email]],
      phone: [''],
      address_street: [''],
      address_city: [''],
      address_state: [''],
      address_zip: [''],
      address_country: [''],
      tax_id: [''],
      payment_terms: [''],
      currency: ['USD'],
      website: [''],
      internal_notes: ['']
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const id = params.get('id');
      if (id && id !== 'new') {
        this.isEditMode = true;
        this.supplierId = +id;
        this.loadSupplier(this.supplierId);
      }
    });
  }

  loadSupplier(id: number): void {
    this.suppliersService.getSupplier(id).subscribe({
      next: (supplier) => {
        this.supplierForm.patchValue(supplier);
      },
      error: (err) => {
        console.error('Error loading supplier', err);
        this.snackBar.open(this.translocoService.translate('suppliers.messages.loadFailed'), this.translocoService.translate('common.close'), { duration: 3000 });
      }
    });
  }

  onSubmit(): void {
    if (this.supplierForm.invalid) return;

    const supplierData: SupplierCreate = this.supplierForm.value;

    this.suppliersService.createSupplier(supplierData).subscribe(supplier => {
      this.snackBar.open(this.translocoService.translate('suppliers.messages.created'), this.translocoService.translate('common.close'), { duration: 3000 });
      this.router.navigate(['/suppliers/list']);
    });
  }
}
