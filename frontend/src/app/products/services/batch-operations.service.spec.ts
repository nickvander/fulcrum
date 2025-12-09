import type { MockedObject } from "vitest";
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { BatchOperationsService } from './batch-operations.service';
import { NotificationService } from '../../core/services/notification.service';

describe('BatchOperationsService', () => {
    let service: BatchOperationsService;
    let httpMock: HttpTestingController;
    let notificationServiceSpy: MockedObject<NotificationService>;

    beforeEach(() => {
        const spy = {
            showSuccess: vi.fn().mockName("NotificationService.showSuccess"),
            showError: vi.fn().mockName("NotificationService.showError")
        };

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                BatchOperationsService,
                { provide: NotificationService, useValue: spy }
            ]
        });

        service = TestBed.inject(BatchOperationsService);
        httpMock = TestBed.inject(HttpTestingController);
        notificationServiceSpy = TestBed.inject(NotificationService) as MockedObject<NotificationService>;
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should call batchUpdatePrices with correct parameters', () => {
        const productIds = [1, 2, 3];
        const priceAdjustment = 10;
        const adjustmentType: 'set' | 'increase' = 'set';

        service.batchUpdatePrices(productIds, priceAdjustment, adjustmentType).subscribe();

        const req = httpMock.expectOne(`${service['apiUrl']}/batch-update-prices`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual({
            product_ids: productIds,
            price_adjustment: priceAdjustment,
            adjustment_type: adjustmentType
        });
    });

    it('should call batchUpdateCategories with correct parameters', () => {
        const productIds = [1, 2, 3];
        const category = 'Electronics';

        service.batchUpdateCategories(productIds, category).subscribe();

        const req = httpMock.expectOne(`${service['apiUrl']}/batch-update-categories`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual({
            product_ids: productIds,
            category: category
        });
    });

    it('should call batchUpdateCustomFields with correct parameters', () => {
        const productIds = [1, 2, 3];
        const customFieldUpdates = { warranty: '12 months', color: 'red' };

        service.batchUpdateCustomFields(productIds, customFieldUpdates).subscribe();

        const req = httpMock.expectOne(`${service['apiUrl']}/batch-update-custom-fields`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toEqual({
            product_ids: productIds,
            custom_field_updates: customFieldUpdates
        });
    });

    it('should call deleteMultipleProducts with correct parameters', () => {
        const productIds = [1, 2, 3];

        service.deleteMultipleProducts(productIds).subscribe();

        const req = httpMock.expectOne(`${service['apiUrl']}/`);
        expect(req.request.method).toBe('DELETE');
        expect(req.request.body).toEqual({ ids: productIds });
    });

    it('should call batchUploadImages with correct parameters', () => {
        const formData = new FormData();

        service.batchUploadImages(formData).subscribe();

        const req = httpMock.expectOne(`${service['apiUrl']}/batch-upload-images`);
        expect(req.request.method).toBe('POST');
        expect(req.request.body).toBe(formData);
    });
});
