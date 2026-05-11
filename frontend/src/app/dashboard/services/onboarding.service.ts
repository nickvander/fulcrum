import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface OnboardingStep {
    key: string;
    label: string;
    description: string;
    complete: boolean;
    optional: boolean;
    warning: boolean;
    action_label: string;
    route: string;
    count: number;
}

export interface OnboardingStatus {
    complete: boolean;
    completed_required: number;
    total_required: number;
    steps: OnboardingStep[];
}

export interface DemoWorkspaceResult {
    created: boolean;
    created_resources: string[];
    supplier_id: number;
    product_id: number;
    purchase_order_id: number;
    message: string;
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
    private apiUrl = `${environment.apiUrl}/onboarding`;

    constructor(private http: HttpClient) { }

    getStatus(): Observable<OnboardingStatus> {
        return this.http.get<OnboardingStatus>(`${this.apiUrl}/status`);
    }

    createDemoWorkspace(): Observable<DemoWorkspaceResult> {
        return this.http.post<DemoWorkspaceResult>(`${this.apiUrl}/demo-workspace`, {});
    }
}
