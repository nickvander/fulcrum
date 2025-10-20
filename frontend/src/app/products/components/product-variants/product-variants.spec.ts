import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ProductVariantsComponent } from './product-variants';
import { ProductVariant } from '../../models/product.model';

describe('ProductVariantsComponent', () => {
  let component: ProductVariantsComponent;
  let fixture: ComponentFixture<ProductVariantsComponent>;

  const mockVariants: ProductVariant[] = [
    {
      id: 1,
      product_id: 1,
      name: 'Red - Large',
      sku: 'RED-L-001',
      price: 29.99,
      stock_quantity: 10,
      attributes: { color: 'red', size: 'large' }
    },
    {
      id: 2,
      product_id: 1,
      name: 'Blue - Medium',
      sku: 'BLUE-M-001',
      price: 24.99,
      stock_quantity: 5,
      attributes: { color: 'blue', size: 'medium' }
    }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MatIconModule,
        MatButtonModule,
        MatInputModule,
        MatSelectModule,
        MatFormFieldModule,
        MatCardModule,
        MatExpansionModule,
        FormsModule,
        ReactiveFormsModule,
        ProductVariantsComponent
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductVariantsComponent);
    component = fixture.componentInstance;
    component.productVariants = [...mockVariants];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with provided variants', () => {
    expect(component.editableVariants.length).toBe(2);
    expect(component.editableVariants[0].name).toBe('Red - Large');
  });

  it('should emit variantsChanged event when variants are updated', () => {
    spyOn(component.variantsChanged, 'emit');

    component.updateVariant(0, 'name', 'Updated Name');
    component.onSaveVariants();

    expect(component.variantsChanged.emit).toHaveBeenCalled();
  });

  it('should add a new variant when onAddVariant is called', () => {
    spyOn(component.addVariant, 'emit');
    component.onAddVariant();
    expect(component.addVariant.emit).toHaveBeenCalled();
  });

  it('should remove a variant when onRemoveVariant is called', () => {
    spyOn(component.variantsChanged, 'emit');

    expect(component.editableVariants.length).toBe(2);
    component.onRemoveVariant(0);
    expect(component.editableVariants.length).toBe(1);
    expect(component.variantsChanged.emit).toHaveBeenCalled();
  });

  it('should update variant property when updateVariant is called', () => {
    component.updateVariant(0, 'price', 39.99);
    expect(component.editableVariants[0].price).toBe(39.99);
  });

  it('should cancel edits when onCancelEdit is called', () => {
    component.updateVariant(0, 'name', 'Changed Name');
    component.onCancelEdit();
    // Check that the change was reverted to original value
    expect(component.editableVariants[0].name).toBe('Red - Large');
  });
});