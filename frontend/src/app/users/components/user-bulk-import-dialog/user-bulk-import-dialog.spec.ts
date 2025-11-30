import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserBulkImportDialogComponent } from './user-bulk-import-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { UserService } from '../../services/user.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('UserBulkImportDialogComponent', () => {
  let component: UserBulkImportDialogComponent;
  let fixture: ComponentFixture<UserBulkImportDialogComponent>;
  let userServiceSpy: jasmine.SpyObj<UserService>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<UserBulkImportDialogComponent>>;
  let snackBarSpy: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    userServiceSpy = jasmine.createSpyObj('UserService', ['bulkImportUsers']);
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);
    snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [UserBulkImportDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: UserService, useValue: userServiceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(UserBulkImportDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should validate file type on selection', () => {
    const file = new File([''], 'test.txt', { type: 'text/plain' });
    const event = { target: { files: [file] } };
    component.onFileSelected(event);
    expect(snackBarSpy.open).toHaveBeenCalledWith('Please select a CSV file', 'Close', { duration: 3000 });
    expect(component.selectedFile).toBeNull();
  });

  it('should accept csv file', () => {
    const file = new File([''], 'test.csv', { type: 'text/csv' });
    const event = { target: { files: [file] } };
    component.onFileSelected(event);
    expect(component.selectedFile).toBe(file);
  });

  it('should call bulkImportUsers on upload', () => {
    const file = new File([''], 'test.csv', { type: 'text/csv' });
    component.selectedFile = file;
    userServiceSpy.bulkImportUsers.and.returnValue(of({ created_users: [], failed_users: [] }));

    component.upload();

    expect(userServiceSpy.bulkImportUsers).toHaveBeenCalledWith(file);
    expect(component.isUploading).toBeFalse();
    expect(component.importResult).toBeDefined();
  });
});
