import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Campaign {
    id: number;
    user_id: number;
    name: string;
    description?: string;
    status: string;
    start_date?: string;
    end_date?: string;
    budget?: number;
    spent: number;
    is_smart_boost: boolean;
    boost_reason?: string;
    created_at: string;
    updated_at?: string;
    events: CampaignEvent[];
    products: CampaignProductSummary[];
    analytics?: CampaignAnalytics;
}

export interface CampaignSummary {
    id: number;
    name: string;
    status: string;
    start_date?: string;
    end_date?: string;
    events_count: number;
    products_count: number;
}

export interface CampaignEvent {
    id: number;
    campaign_id?: number;
    connector_id?: number;
    name: string;
    channel_type: string;
    content_subject?: string;
    content_body?: string;
    content_image_url?: string;
    content_json?: any;
    scheduled_at?: string;
    published_at?: string;
    status: string;
    external_id?: string;
    external_url?: string;
    error_message?: string;
    created_at: string;
    updated_at?: string;
    products: CampaignProductSummary[];
}

export interface CampaignProductSummary {
    id: number;
    name: string;
    sku?: string;
    image_url?: string;
}

export interface CampaignAnalytics {
    total_impressions: number;
    total_clicks: number;
    total_reach: number;
    total_likes: number;
    total_shares: number;
    total_comments: number;
    total_conversions: number;
    conversion_value: number;
    total_cost: number;
    cpc?: number;
    cpm?: number;
    revenue_attributed: number;
    roi_percentage?: number;
    last_synced_at?: string;
}

export interface MarketingConnector {
    id: number;
    user_id: number;
    name: string;
    connector_type: string;
    channel_type: string;
    config_json?: any;
    is_active: boolean;
    last_used_at?: string;
    created_at: string;
    updated_at?: string;
}

export interface ConnectorCreate {
    name: string;
    connector_type: string;
    channel_type: string;
    config_json?: any;
    api_key?: string;
    api_secret?: string;
    is_active?: boolean;
}

export interface CampaignCreate {
    name: string;
    description?: string;
    start_date?: string;
    end_date?: string;
    budget?: number;
    product_ids?: number[];
    events?: CampaignEventCreate[];
}

export interface CampaignEventCreate {
    name: string;
    channel_type: string;
    connector_id?: number;
    content_subject?: string;
    content_body?: string;
    content_image_url?: string;
    content_json?: any;
    scheduled_at?: string;
    product_ids?: number[];
}

export interface CampaignEventUpdate {
    name?: string;
    channel_type?: string;
    connector_id?: number;
    content_subject?: string;
    content_body?: string;
    content_image_url?: string;
    content_json?: any;
    scheduled_at?: string;
    status?: string;
    product_ids?: number[];
}

export interface SmartBoostRecommendation {
    product_id: number;
    product_name: string;
    product_sku?: string;
    reason: string;
    recommended_channels: string[];
    suggested_discount_percent?: number;
    confidence_score: number;
}

export interface ContentGenerationResponse {
    research: any;
    content: any;
    image_concept: any;
    generated_image_url?: string;
    event_id?: number;
}

// Email provider presets (matching backend)
export const EMAIL_PROVIDER_PRESETS = {
    gmail: {
        host: 'smtp.gmail.com',
        port: 587,
        use_tls: true,
        use_ssl: false,
        display_name: 'Gmail',
        help_text: 'Use an App Password (not your regular password). Enable 2FA in Google Account → Security → App Passwords.',
    },
    outlook: {
        host: 'smtp.office365.com',
        port: 587,
        use_tls: true,
        use_ssl: false,
        display_name: 'Outlook / Office 365',
        help_text: 'Use your Microsoft account password or an App Password if 2FA is enabled.',
    },
    yahoo: {
        host: 'smtp.mail.yahoo.com',
        port: 587,
        use_tls: true,
        use_ssl: false,
        display_name: 'Yahoo Mail',
        help_text: 'Generate an App Password in Yahoo Account → Security.',
    },
    custom: {
        display_name: 'Custom SMTP Server',
        help_text: 'Enter your SMTP server details manually.',
    },
};

@Injectable({
    providedIn: 'root'
})
export class MarketingService {
    private readonly baseUrl = `${environment.apiUrl}/marketing`;

    constructor(private http: HttpClient) { }

    // ===========================
    // Campaigns
    // ===========================

    getCampaigns(status?: string): Observable<CampaignSummary[]> {
        const url = `${this.baseUrl}/campaigns`;
        if (status) {
            return this.http.get<CampaignSummary[]>(url, { params: { status } });
        }
        return this.http.get<CampaignSummary[]>(url);
    }

    getCampaign(id: number): Observable<Campaign> {
        return this.http.get<Campaign>(`${this.baseUrl}/campaigns/${id}`);
    }

    createCampaign(campaign: CampaignCreate): Observable<Campaign> {
        return this.http.post<Campaign>(`${this.baseUrl}/campaigns`, campaign);
    }

    updateCampaign(id: number, campaign: Partial<CampaignCreate>): Observable<Campaign> {
        return this.http.put<Campaign>(`${this.baseUrl}/campaigns/${id}`, campaign);
    }

    deleteCampaign(id: number): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/campaigns/${id}`);
    }

    // ===========================
    // Campaign Events
    // ===========================

    createEvent(campaignId: number, event: CampaignEventCreate): Observable<CampaignEvent> {
        return this.http.post<CampaignEvent>(`${this.baseUrl}/campaigns/${campaignId}/events`, event);
    }

    updateEvent(eventId: number, event: Partial<CampaignEventCreate>): Observable<CampaignEvent> {
        return this.http.put<CampaignEvent>(`${this.baseUrl}/events/${eventId}`, event);
    }

    deleteEvent(eventId: number): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/events/${eventId}`);
    }

    getEvents(startDate: string, endDate: string): Observable<CampaignEvent[]> {
        return this.http.get<CampaignEvent[]>(`${this.baseUrl}/events`, {
            params: { start_date: startDate, end_date: endDate }
        });
    }

    publishEvent(eventId: number): Observable<{ success: boolean; external_id?: string; external_url?: string }> {
        return this.http.post<{ success: boolean; external_id?: string; external_url?: string }>(
            `${this.baseUrl}/events/${eventId}/publish`,
            {}
        );
    }

    // ===========================
    // Quick Posts
    // ===========================

    getQuickPosts(limit: number = 20): Observable<CampaignEvent[]> {
        return this.http.get<CampaignEvent[]>(`${this.baseUrl}/quick-posts`, {
            params: { limit: limit.toString() }
        });
    }

    createQuickPost(event: CampaignEventCreate): Observable<CampaignEvent> {
        return this.http.post<CampaignEvent>(`${this.baseUrl}/quick-posts`, event);
    }

    // ===========================
    // Connectors
    // ===========================

    getConnectors(activeOnly: boolean = true): Observable<MarketingConnector[]> {
        return this.http.get<MarketingConnector[]>(`${this.baseUrl}/connectors`, {
            params: { active_only: activeOnly.toString() }
        });
    }

    createConnector(connector: ConnectorCreate): Observable<MarketingConnector> {
        return this.http.post<MarketingConnector>(`${this.baseUrl}/connectors`, connector);
    }

    updateConnector(id: number, connector: Partial<ConnectorCreate>): Observable<MarketingConnector> {
        return this.http.put<MarketingConnector>(`${this.baseUrl}/connectors/${id}`, connector);
    }

    deleteConnector(id: number): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/connectors/${id}`);
    }

    testConnector(id: number): Observable<{ valid: boolean }> {
        return this.http.post<{ valid: boolean }>(`${this.baseUrl}/connectors/${id}/test`, {});
    }

    // ===========================
    // Smart Boost
    // ===========================

    getSmartBoostRecommendations(): Observable<SmartBoostRecommendation[]> {
        return this.http.get<SmartBoostRecommendation[]>(`${this.baseUrl}/smart-boost`);
    }

    // ===========================
    // AI Content Generation
    // ===========================

    getTonePresets(): Observable<TonePreset[]> {
        return this.http.get<TonePreset[]>(`${this.baseUrl}/tone-presets`);
    }

    generateContent(
        productId: number,
        platform: string,
        tone: string = 'Professional',
        generateImage: boolean = true,
        customPrompt?: string
    ): Observable<ContentGenerationResponse> {
        return this.http.post<ContentGenerationResponse>(`${this.baseUrl}/generate-content`, {
            product_id: productId,
            platform,
            tone,
            generate_image: generateImage,
            custom_prompt: customPrompt
        });
    }
}

// TonePreset interface
export interface TonePreset {
    id: string;
    name: string;
    prompt: string;
    description: string;
}
