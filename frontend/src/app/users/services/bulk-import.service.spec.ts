import type { MockedObject } from "vitest";
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { BulkImportService } from './bulk-import.service';
import { UserService } from './user.service';

describe('BulkImportService', () => {
    let service: BulkImportService;
    let userServiceMock: MockedObject<UserService>;

    beforeEach(() => {
        // Create mock UserService
        userServiceMock = {
            bulkImportUsers: vi.fn().mockName("UserService.bulkImportUsers")
        } as unknown as MockedObject<UserService>;

        TestBed.configureTestingModule({
            providers: [
                BulkImportService,
                { provide: UserService, useValue: userServiceMock }
            ]
        });

        service = TestBed.inject(BulkImportService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('validateFile', () => {
        it('should validate CSV file with .csv extension', () => {
            const file = new File(['test'], 'test.csv', { type: 'text/csv' });
            const result = service.validateFile(file);
            expect(result.valid).toBe(true);
            expect(result.error).toBeUndefined();
        });

        it('should validate CSV file with text/csv MIME type', () => {
            const file = new File(['test'], 'test.txt', { type: 'text/csv' });
            const result = service.validateFile(file);
            expect(result.valid).toBe(true);
        });

        it('should reject non-CSV file', () => {
            const file = new File(['test'], 'test.txt', { type: 'text/plain' });
            const result = service.validateFile(file);
            expect(result.valid).toBe(false);
            expect(result.error).toBe('Please select a CSV file');
        });

        it('should reject file with wrong extension and MIME type', () => {
            const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const result = service.validateFile(file);
            expect(result.valid).toBe(false);
        });
    });

    describe('processFile', () => {
        it('should call userService.bulkImportUsers', async () => {
            const file = new File(['test'], 'test.csv', { type: 'text/csv' });
            const mockResult = {
                created_users: [{ email: 'test@example.com', temporary_password: 'pass123' }],
                failed_users: []
            } as any;

            userServiceMock.bulkImportUsers.mockReturnValue(of(mockResult));

            service.processFile(file).subscribe(result => {
                expect(result).toEqual(mockResult);
                expect(userServiceMock.bulkImportUsers).toHaveBeenCalledWith(file);
                ;
            });
        });

        it('should propagate errors from userService', async () => {
            const file = new File(['test'], 'test.csv', { type: 'text/csv' });
            const error = { error: { detail: 'Import failed' } } as any;

            userServiceMock.bulkImportUsers.mockReturnValue(throwError(() => error));

            service.processFile(file).subscribe({
                next: () => expect.fail('should have errored'),
                error: (err) => {
                    expect(err).toEqual(error);
                    ;
                }
            });
        });
    });

    describe('getTemplateContent', () => {
        it('should return CSV template with headers and example row', () => {
            const content = service.getTemplateContent();
            expect(content).toContain('email,first_name,last_name,user_type');
            expect(content).toContain('user@example.com,John,Doe,employee');
        });
    });

    describe('formatResultsAsCsv', () => {
        it('should format results as CSV', () => {
            const users = [
                { email: 'user1@test.com', temporary_password: 'pass1' },
                { email: 'user2@test.com', temporary_password: 'pass2' }
            ];

            const csv = service.formatResultsAsCsv(users);

            expect(csv).toContain('Email,Temporary Password');
            expect(csv).toContain('user1@test.com,pass1');
            expect(csv).toContain('user2@test.com,pass2');
        });

        it('should handle empty results', () => {
            const csv = service.formatResultsAsCsv([]);
            expect(csv).toBe('Email,Temporary Password');
        });
    });
});
