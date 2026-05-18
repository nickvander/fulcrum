import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type AlertType = 'low_margin' | 'sales_dip' | 'stockout_risk';

export interface AlertRule {
  id: number;
  user_id: number;
  alert_type: AlertType;
  threshold: number;
  window_days: number;
  cooldown_minutes: number;
  enabled: boolean;
  notify_email: string;
  last_evaluated_at?: string | null;
  last_triggered_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AlertRuleCreate {
  alert_type: AlertType;
  threshold: number;
  window_days?: number;
  cooldown_minutes?: number;
  enabled?: boolean;
  notify_email: string;
}

export interface AlertRuleUpdate {
  threshold?: number;
  window_days?: number;
  cooldown_minutes?: number;
  enabled?: boolean;
  notify_email?: string;
}

export interface AlertEvaluationResult {
  rule_id: number;
  triggered: boolean;
  payload: Record<string, unknown>;
  notification_sent: boolean;
  skipped_reason?: string | null;
}

export interface AlertEvent {
  id: number;
  alert_rule_id: number;
  triggered_at: string;
  payload?: Record<string, unknown> | null;
  notification_sent: boolean;
  error?: string | null;
}

/**
 * Thin HTTP wrapper around the backend `/api/v1/alerts/rules` CRUD
 * surface shipped in commit 21eff68. Pairs with `AlertsPageComponent`
 * which owns the list + add/edit dialog + delete confirmation.
 */
@Injectable({ providedIn: 'root' })
export class AlertsService {
  private apiUrl = `${environment.apiUrl}/alerts`;

  constructor(private http: HttpClient) {}

  list(): Observable<AlertRule[]> {
    return this.http.get<AlertRule[]>(`${this.apiUrl}/rules`);
  }

  get(id: number): Observable<AlertRule> {
    return this.http.get<AlertRule>(`${this.apiUrl}/rules/${id}`);
  }

  create(rule: AlertRuleCreate): Observable<AlertRule> {
    return this.http.post<AlertRule>(`${this.apiUrl}/rules`, rule);
  }

  update(id: number, patch: AlertRuleUpdate): Observable<AlertRule> {
    return this.http.patch<AlertRule>(`${this.apiUrl}/rules/${id}`, patch);
  }

  delete(id: number): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>(`${this.apiUrl}/rules/${id}`);
  }

  /**
   * Force-evaluate a rule now. The backend bypasses the cooldown on
   * this path so the operator gets immediate feedback that the SMTP
   * wiring is correct.
   */
  test(id: number): Observable<AlertEvaluationResult> {
    return this.http.post<AlertEvaluationResult>(`${this.apiUrl}/rules/${id}/test`, {});
  }

  events(id: number): Observable<AlertEvent[]> {
    return this.http.get<AlertEvent[]>(`${this.apiUrl}/rules/${id}/events`);
  }
}
