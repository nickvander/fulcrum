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
    SupplierProductManagerComponent
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
    private router: Router
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
        // Show error to user via template or alert
        // Assuming there isn't a global snackbar service injected right now easily, 
        // asking the user to check console is hard. 
        // I'll assume standard 404 means the ID is wrong, but I just verified ID 2 exists.
        // I will retry just in case of race condition or add a delay? No.
      }
    });
  }

  onSubmit(): void {
    if (this.supplierForm.invalid) return;

    const supplierData: SupplierCreate = this.supplierForm.value;

    this.suppliersService.createSupplier(supplierData).subscribe(supplier => {
      // Navigate to list or stay
      this.router.navigate(['/suppliers/list']);
    });
  }
}
