import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface Account {
    id: number;
    name: string;
    connected: boolean;
}

@Component({
    selector: 'app-marketplace-settings',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        RouterModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatFormFieldModule,
        MatInputModule,
        MatSnackBarModule
    ],
    templateUrl: './marketplace-settings.html',
    styleUrl: './marketplace-settings.scss',
})
export class MarketplaceSettingsComponent implements OnInit {
    marketplaceType = '';
    marketplaceName = '';
    showAddForm = false;
    accounts: Account[] = [];

    newAccount = {
        name: '',
        clientId: '',
        clientSecret: '',
        redirectUri: ''
    };

    get defaultRedirectUri(): string {
        return `http://localhost:4200/marketplaces/${this.marketplaceType}/callback`;
    }

    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private http: HttpClient,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit(): void {
        this.route.paramMap.subscribe(params => {
            this.marketplaceType = params.get('type') || 'amazon';
            this.marketplaceName = this.marketplaceType === 'amazon' ? 'Amazon' : 'MercadoLibre';
            this.newAccount.redirectUri = this.defaultRedirectUri;
            this.loadAccounts();
        });
    }

    loadAccounts(): void {
        // For now, we'll simulate accounts from the credentials API
        this.http.get<any>(`${environment.apiUrl}/settings/marketplace`).subscribe({
            next: (settings) => {
                // Check if this marketplace has credentials
                const key = this.marketplaceType.toLowerCase();
                if (settings[key] && settings[key].connected) {
                    this.accounts = [{
                        id: 1,
                        name: `${this.marketplaceName} Account`,
                        connected: true
                    }];
                } else {
                    this.accounts = [];
                }
            },
            error: () => {
                this.accounts = [];
            }
        });
    }

    saveAndConnect(): void {
        const payload = {
            marketplace: this.marketplaceType,
            client_id: this.newAccount.clientId,
            client_secret: this.newAccount.clientSecret,
            redirect_uri: this.newAccount.redirectUri,
            name: this.newAccount.name
        };

        this.snackBar.open('Saving credentials and connecting...', '', { duration: 2000 });

        // Save first, then redirect to OAuth
        this.http.post(`${environment.apiUrl}/settings/marketplace`, payload).subscribe({
            next: () => {
                // Get auth URL and redirect
                this.http.get<{ auth_url: string }>(`${environment.apiUrl}/marketplace-credentials/by-name/${this.marketplaceType}/authorize`).subscribe({
                    next: (response) => {
                        window.location.href = response.auth_url;
                    },
                    error: (err) => {
                        console.error('Auth error:', err);
                        this.snackBar.open(`Failed to get authorization URL.`, 'Close', { duration: 5000 });
                    }
                });
            },
            error: (err) => {
                console.error('Save error:', err);
                this.snackBar.open(`Failed to save credentials.`, 'Close', { duration: 5000 });
            }
        });
    }

    reconnect(accountId: number): void {
        this.http.get<{ auth_url: string }>(`${environment.apiUrl}/marketplace-credentials/by-name/${this.marketplaceType}/authorize`).subscribe({
            next: (response) => {
                window.location.href = response.auth_url;
            },
            error: (err) => {
                console.error('Auth error:', err);
                this.snackBar.open('Failed to get authorization URL.', 'Close', { duration: 5000 });
            }
        });
    }

    deleteAccount(accountId: number): void {
        if (confirm('Are you sure you want to remove this account?')) {
            // TODO: Implement delete API
            this.snackBar.open('Account removed.', 'Close', { duration: 3000 });
            this.accounts = this.accounts.filter(a => a.id !== accountId);
        }
    }
}
