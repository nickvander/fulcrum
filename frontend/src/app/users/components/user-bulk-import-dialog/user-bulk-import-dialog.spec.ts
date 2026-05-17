import type { MockedObject, MockInstance } from "vitest";
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserBulkImportDialogComponent } from './user-bulk-import-dialog';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BulkImportService } from '../../services/bulk-import.service';
import { of, throwError } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('UserBulkImportDialogComponent', () => {
    let component: UserBulkImportDialogComponent;
    let fixture: ComponentFixture<UserBulkImportDialogComponent>;
    let bulkImportServiceSpy: MockedObject<BulkImportService>;
    let dialogRefSpy: MockedObject<MatDialogRef<UserBulkImportDialogComponent>>;
    let snackBarOpenSpy: MockInstance;

    beforeEach(async () => {
        bulkImportServiceSpy = {
            validateFile: vi.fn().mockName("BulkImportService.validateFile"),
            processFile: vi.fn().mockName("BulkImportService.processFile"),
            getTemplateContent: vi.fn().mockName("BulkImportService.getTemplateContent"),
            formatResultsAsCsv: vi.fn().mockName("BulkImportService.formatResultsAsCsv")
        } as unknown as MockedObject<BulkImportService>;
        dialogRefSpy = {
            close: vi.fn().mockName("MatDialogRef.close")
        } as unknown as MockedObject<MatDialogRef<UserBulkImportDialogComponent>>;

        await TestBed.configureTestingModule({
            imports: [
                UserBulkImportDialogComponent,
                NoopAnimationsModule,
                TranslocoTestingModule.forRoot({ langs: { en: {}, 'es-MX': {} } }),
            ],
            // NO_ERRORS_SCHEMA prevents Material child components from rendering, which
            // was the original timeout cause documented before this file was un-skipped.
            schemas: [NO_ERRORS_SCHEMA],
            providers: [
                { provide: MatDialogRef, useValue: dialogRefSpy },
                { provide: BulkImportService, useValue: bulkImportServiceSpy },
                { provide: MAT_DIALOG_DATA, useValue: {} }
            ]
        })
            .overrideComponent(UserBulkImportDialogComponent, {
                set: {
                    providers: [
                        { provide: BulkImportService, useValue: bulkImportServiceSpy }
                    ]
                }
            })
            .compileComponents();

        fixture = TestBed.createComponent(UserBulkImportDialogComponent);
        component = fixture.componentInstance;
        // Spy on the real MatSnackBar instance Angular DI injected into the component —
        // a useValue: { open: vi.fn() } override doesn't survive MatSnackBarModule's
        // own provider chain in standalone components.
        snackBarOpenSpy = vi.spyOn((component as any).snackBar as MatSnackBar, 'open');
        // Don't call detectChanges() here - it triggers Material component initialization
    });

    afterEach(() => {
        fixture.destroy();
        vi.restoreAllMocks();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    describe('onFileSelected', () => {
        it('should show error for invalid file', () => {
            const file = new File([''], 'test.txt', { type: 'text/plain' });
            const event = { target: { files: [file] } } as any;

            bulkImportServiceSpy.validateFile.mockReturnValue({
                valid: false,
                error: 'Please select a CSV file'
            });

            component.onFileSelected(event);

            expect(bulkImportServiceSpy.validateFile).toHaveBeenCalledWith(file);
            expect(snackBarOpenSpy).toHaveBeenCalledWith('Please select a CSV file', 'en.common.close', { duration: 3000 });
            expect(component.selectedFile).toBeNull();
        });

        it('should accept valid CSV file', () => {
            const file = new File([''], 'test.csv', { type: 'text/csv' });
            const event = { target: { files: [file] } } as any;

            bulkImportServiceSpy.validateFile.mockReturnValue({ valid: true });

            component.onFileSelected(event);

            expect(component.selectedFile).toBe(file);
            expect(component.importResult).toBeNull();
        });
    });

    describe('upload', () => {
        it('should call bulkImportService.processFile and handle success', () => {
            const file = new File([''], 'test.csv', { type: 'text/csv' });
            const mockResult = {
                created_users: [{ email: 'test@example.com', temporary_password: 'pass123' }],
                failed_users: []
            } as any;

            component.selectedFile = file;
            bulkImportServiceSpy.processFile.mockReturnValue(of(mockResult));

            component.upload();

            expect(bulkImportServiceSpy.processFile).toHaveBeenCalledWith(file);
            expect(component.isUploading).toBe(false);
            expect(component.importResult).toEqual(mockResult);
            expect(snackBarOpenSpy).toHaveBeenCalledWith('en.users.messages.importSuccess', 'en.common.close', { duration: 3000 });
        });

        it('should handle import with failures', () => {
            const file = new File([''], 'test.csv', { type: 'text/csv' });
            const mockResult = {
                created_users: [],
                failed_users: [{ email: 'bad@example.com', error: 'Invalid data' }]
            } as any;

            component.selectedFile = file;
            bulkImportServiceSpy.processFile.mockReturnValue(of(mockResult));

            component.upload();

            expect(component.isUploading).toBe(false);
            expect(snackBarOpenSpy).toHaveBeenCalledWith('en.users.messages.importWithErrors', 'en.common.close', { duration: 5000 });
        });

        it('should surface backend detail when error has no code (legacy path)', () => {
            const file = new File([''], 'test.csv', { type: 'text/csv' });
            const error = { error: { detail: 'Server error' } };

            component.selectedFile = file;
            bulkImportServiceSpy.processFile.mockReturnValue(throwError(() => error));

            component.upload();

            expect(component.isUploading).toBe(false);
            expect(snackBarOpenSpy).toHaveBeenCalledWith('Server error', 'en.common.close', { duration: 5000 });
        });

        it('should translate the error code when backend returns {code, params}', () => {
            const file = new File([''], 'test.csv', { type: 'text/csv' });
            const error = { error: { code: 'apiErrors.product.skuExists', params: { sku: 'ABC' }, detail: 'A product with SKU ABC already exists.' } };

            component.selectedFile = file;
            bulkImportServiceSpy.processFile.mockReturnValue(throwError(() => error));

            component.upload();

            expect(component.isUploading).toBe(false);
            // TranslocoTestingModule has empty langs, so translate() returns the key —
            // that's enough to prove translateApiError took the code branch.
            expect(snackBarOpenSpy).toHaveBeenCalledWith('en.apiErrors.product.skuExists', 'en.common.close', { duration: 5000 });
        });

        it('should not upload if no file selected', () => {
            component.selectedFile = null;
            component.upload();
            expect(bulkImportServiceSpy.processFile).not.toHaveBeenCalled();
        });
    });

    describe('downloadTemplate', () => {
        it('should download template file', () => {
            const templateContent = 'email,first_name,last_name,user_type\nuser@example.com,John,Doe,employee';
            bulkImportServiceSpy.getTemplateContent.mockReturnValue(templateContent);

            vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:mock-url');
            vi.spyOn(window.URL, 'revokeObjectURL');
            vi.spyOn(document, 'createElement');

            component.downloadTemplate();

            expect(bulkImportServiceSpy.getTemplateContent).toHaveBeenCalled();
            expect(window.URL.createObjectURL).toHaveBeenCalled();
            expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
        });
    });

    describe('close', () => {
        it('should close with true if import result exists', () => {
            component.importResult = { created_users: [], failed_users: [] };
            component.close();
            expect(dialogRefSpy.close).toHaveBeenCalledWith(true);
        });

        it('should close with false if no import result', () => {
            component.importResult = null;
            component.close();
            expect(dialogRefSpy.close).toHaveBeenCalledWith(false);
        });
    });

    describe('copyAll', () => {
        it('should copy all results as CSV', async () => {
            const users = [{ email: 'user@test.com', temporary_password: 'pass' }];
            component.importResult = { created_users: users, failed_users: [] };

            bulkImportServiceSpy.formatResultsAsCsv.mockReturnValue('Email,Temporary Password\nuser@test.com,pass');
            const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockReturnValue(Promise.resolve());

            component.copyAll();
            await Promise.resolve(); // let the writeText().then() callback run

            expect(bulkImportServiceSpy.formatResultsAsCsv).toHaveBeenCalledWith(users);
            expect(writeTextSpy).toHaveBeenCalled();
            expect(snackBarOpenSpy).toHaveBeenCalledWith('en.common.messages.copied', 'en.common.close', { duration: 2000 });
        });

        it('should not copy if no import result', () => {
            component.importResult = null;
            const writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText');

            component.copyAll();

            expect(writeTextSpy).not.toHaveBeenCalled();
        });
    });
});
