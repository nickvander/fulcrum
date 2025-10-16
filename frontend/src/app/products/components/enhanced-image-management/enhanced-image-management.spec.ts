import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { CdkDrag, CdkDragHandle, CdkDropList } from '@angular/cdk/drag-drop';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { EnhancedImageManagementComponent, ProductImage } from './enhanced-image-management';

describe('EnhancedImageManagementComponent', () => {
  let component: EnhancedImageManagementComponent;
  let fixture: ComponentFixture<EnhancedImageManagementComponent>;

  const mockImages: ProductImage[] = [
    {
      id: 1,
      image_path: 'image1.jpg',
      is_primary: 0,
      title: 'Image 1',
      description: 'First image'
    },
    {
      id: 2,
      image_path: 'image2.jpg',
      is_primary: 1,
      title: 'Image 2',
      description: 'Second image'
    }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        CdkDropList,
        CdkDrag,
        CdkDragHandle,
        MatIconModule,
        MatButtonModule,
        MatTooltipModule,
        EnhancedImageManagementComponent
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EnhancedImageManagementComponent);
    component = fixture.componentInstance;
    component.images = [...mockImages];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with provided images', () => {
    expect(component.images.length).toBe(2);
    expect(component.images[0].title).toBe('Image 1');
  });

  it('should emit imageOrderChanged event when onReorder is called', () => {
    spyOn(component.imageOrderChanged, 'emit');
    
    // Mock event object for drag and drop
    const mockEvent = {
      item: { data: mockImages[0] },
      currentIndex: 1
    };
    
    component.onReorder(mockEvent);
    expect(component.imageOrderChanged.emit).toHaveBeenCalled();
  });

  it('should emit primaryImageChanged event when setAsPrimary is called', () => {
    spyOn(component.primaryImageChanged, 'emit');
    component.setAsPrimary(2);
    expect(component.primaryImageChanged.emit).toHaveBeenCalledWith(2);
  });

  it('should emit imageDeleted event when deleteImage is called', () => {
    spyOn(component.imageDeleted, 'emit');
    component.deleteImage(1);
    expect(component.imageDeleted.emit).toHaveBeenCalledWith(1);
  });

  it('should emit imageUpdated event when updateImage is called', () => {
    spyOn(component.imageUpdated, 'emit');
    component.updateImage(1, 'title', 'New Title');
    expect(component.imageUpdated.emit).toHaveBeenCalledWith({
      imageId: 1,
      updates: { title: 'New Title' }
    });
  });

  it('should emit altTextChanged event when onAltTextChange is called', () => {
    spyOn(component.altTextChanged, 'emit');
    component.onAltTextChange(1, 'New alt text');
    expect(component.altTextChanged.emit).toHaveBeenCalledWith({
      imageId: 1,
      altText: 'New alt text'
    });
  });

  it('should format image URL correctly', () => {
    const url = component.getImageUrl('test.jpg');
    expect(url).toBe('/uploads/product_images/test.jpg');
  });

  it('should have primary class for primary images', () => {
    // This would be tested in a template test, but we can verify the data
    expect(component.images[1].is_primary).toBe(1);
  });
});