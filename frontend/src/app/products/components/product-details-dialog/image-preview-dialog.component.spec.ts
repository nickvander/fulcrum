import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { ImagePreviewDialogComponent } from './image-preview-dialog.component';

describe('ImagePreviewDialogComponent', () => {
  let component: ImagePreviewDialogComponent;
  let fixture: ComponentFixture<ImagePreviewDialogComponent>;
  let mockDialogRef: any;

  beforeEach(async () => {
    mockDialogRef = {
      close: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [
        MatDialogModule,
        MatIconModule,
        ImagePreviewDialogComponent
      ],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { imageUrl: 'test-image.jpg', title: 'Test Image' } },
        { provide: MatDialogRef, useValue: mockDialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ImagePreviewDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display the image with correct src', () => {
    const img = fixture.nativeElement.querySelector('img');
    expect(img).toBeTruthy();
    expect(img.src).toContain('test-image.jpg');
  });

  it('should close the dialog when close button is clicked', () => {
    const closeBtn = fixture.nativeElement.querySelector('.close-btn');
    closeBtn.click();
    expect(mockDialogRef.close).toHaveBeenCalled();
  });
});
