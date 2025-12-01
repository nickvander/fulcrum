import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { UserService } from './user.service';

/**
 * Service to handle bulk user import logic.
 * Extracted from UserBulkImportDialogComponent to enable easier testing
 * and avoid test timeouts caused by Material component observables.
 */
@Injectable()
export class BulkImportService {
    constructor(private userService: UserService) { }

    /**
     * Validates that a file is a CSV file
     */
    validateFile(file: File): { valid: boolean; error?: string } {
        if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
            return { valid: false, error: 'Please select a CSV file' };
        }
        return { valid: true };
    }

    /**
     * Process a CSV file for bulk user import
     */
    processFile(file: File): Observable<any> {
        return this.userService.bulkImportUsers(file);
    }

    /**
     * Generate CSV template content for user import
     */
    getTemplateContent(): string {
        return 'email,first_name,last_name,user_type\nuser@example.com,John,Doe,employee';
    }

    /**
     * Format import results as CSV for copying to clipboard
     */
    formatResultsAsCsv(createdUsers: any[]): string {
        const headers = ['Email', 'Temporary Password'];
        const rows = createdUsers.map((u: any) => `${u.email},${u.temporary_password}`);
        return [headers.join(','), ...rows].join('\n');
    }
}
