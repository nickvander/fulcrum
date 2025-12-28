import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { SuppliersService } from '../suppliers.service';
import { Supplier, SupplierCreate } from '../../shared/models/supplier.model';

@Component({
  selector: 'app-supplier-detail',
  templateUrl: './supplier-detail.component.html',
  styleUrls: ['./supplier-detail.component.scss'],
  standalone: false
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
        // Logic to fetch supplier would go here
        // For now, assuming create-only flow or placeholder for edit
        this.isEditMode = true;
        this.supplierId = +id;
        // this.loadSupplier(this.supplierId); 
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
