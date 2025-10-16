import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BatchActionToolbarComponent } from './batch-action-toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('BatchActionToolbarComponent', () => {
  let component: BatchActionToolbarComponent;
  let fixture: ComponentFixture<BatchActionToolbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BatchActionToolbarComponent, MatButtonModule, MatIconModule, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(BatchActionToolbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display the correct number of selected items', () => {
    component.selectedCount = 3;
    fixture.detectChanges();
    
    const compiled = fixture.nativeElement;
    expect(compiled.textContent).toContain('3 selected');
  });

  it('should emit deleteSelected event when delete button is clicked', () => {
    spyOn(component.deleteSelected, 'emit');
    component.selectedCount = 3;
    fixture.detectChanges();
    
    const deleteButton = fixture.nativeElement.querySelector('button[color="warn"]');
    deleteButton.click();
    
    expect(component.deleteSelected.emit).toHaveBeenCalled();
  });

  it('should emit selectAll event when "Select All" button is clicked', () => {
    spyOn(component.selectAll, 'emit');
    component.selectedCount = 0;
    fixture.detectChanges();
    
    const selectAllButton = fixture.nativeElement.querySelector('button');
    selectAllButton.click();
    
    expect(component.selectAll.emit).toHaveBeenCalled();
  });

  it('should emit deselectAll event when "Deselect All" button is clicked', () => {
    spyOn(component.deselectAll, 'emit');
    component.selectedCount = 5;
    fixture.detectChanges();
    
    const deselectButton = fixture.nativeElement.querySelector('button');
    // The first button is "Select All", second is "Deselect All"
    const buttons = fixture.nativeElement.querySelectorAll('button');
    if (buttons.length > 1) {
      buttons[1].click();
    } else {
      // If only one button exists, it might be "Deselect All"
      buttons[0].click();
    }
    
    expect(component.deselectAll.emit).toHaveBeenCalled();
  });

  it('should emit closeToolbar event when close button is clicked', () => {
    spyOn(component.closeToolbar, 'emit');
    fixture.detectChanges();
    
    const closeButton = fixture.nativeElement.querySelector('.close-button');
    closeButton.click();
    
    expect(component.closeToolbar.emit).toHaveBeenCalled();
  });

  it('should show "Select All" button when no items are selected', () => {
    component.selectedCount = 0;
    fixture.detectChanges();
    
    const compiled = fixture.nativeElement;
    expect(compiled.textContent).toContain('Select All');
  });

  it('should show "Deselect All" button when items are selected', () => {
    component.selectedCount = 2;
    fixture.detectChanges();
    
    const compiled = fixture.nativeElement;
    expect(compiled.textContent).toContain('Deselect All');
  });
});