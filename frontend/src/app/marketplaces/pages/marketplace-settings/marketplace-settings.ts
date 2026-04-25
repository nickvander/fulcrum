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
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { HttpClient } from '@angular/common/http';
import { TranslocoModule, TranslocoService } from '@ngneat/transloco';
import { environment } from '../../../../environments/environment';
import { ConfirmationDialog, ConfirmationDialogData } from '../../../shared/components/confirmation-dialog/confirmation-dialog';

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
        MatInputModule,
        MatSnackBarModule,
        MatDialogModule,
        TranslocoModule
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
        private snackBar: MatSnackBar,
        private dialog: MatDialog,
        private translocoService: TranslocoService
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
        // Get the marketplace ID first
        this.http.get<any[]>(`${environment.apiUrl}/marketplace/`).subscribe({
            next: (marketplaces) => {
                const mp = marketplaces.find(m => m.name.toLowerCase() === this.marketplaceName.toLowerCase());
                if (mp) {
                    // Check if credentials exist for this marketplace
                    this.http.get<any>(`${environment.apiUrl}/marketplace-credentials/${mp.id}`).subscribe({
                        next: (cred) => {
                            this.accounts = [{
                                id: cred.id,
                                name: `${this.marketplaceName} Account`,
                                connected: true
                            }];
                        },
                        error: (err) => {
                            if (err.status === 404) {
                                this.accounts = [];
                            } else {
                                console.error('Failed to load credentials:', err);
                            }
                        }
                    });
                }
            },
            error: (err) => {
                console.error('Failed to load marketplaces:', err);
                this.accounts = [];
            }
        });
    }

    saveAndConnect(): void {
        // We don't need to post to /settings/marketplace anymore. 
        // Just redirect to the authorization URL.
        this.http.get<{ auth_url: string }>(`${environment.apiUrl}/marketplace-credentials/by-name/${this.marketplaceType}/authorize`).subscribe({
            next: (response) => {
                window.location.href = response.auth_url;
            },
            error: (err) => {
                console.error('Auth error:', err);
                this.snackBar.open(this.translocoService.translate('marketplaces.errors.authUrlFailed'), this.translocoService.translate('common.close'), { duration: 5000 });
            }
        });
    }

    reconnect(accountId: number): void {
        this.saveAndConnect();
    }

    deleteAccount(accountId: number): void {
        const dialogRef = this.dialog.open(ConfirmationDialog, {
            data: {
                title: this.translocoService.translate('marketplaces.removeAccountTitle'),
                message: this.translocoService.translate('marketplaces.removeAccountConfirm')
            } as ConfirmationDialogData
        });

        dialogRef.afterClosed().subscribe(confirmed => {
            if (confirmed) {
                this.http.delete(`${environment.apiUrl}/marketplace-credentials/${accountId}`).subscribe({
                    next: () => {
                        this.snackBar.open(this.translocoService.translate('marketplaces.messages.accountRemoved'), this.translocoService.translate('common.close'), { duration: 3000 });
                        this.accounts = this.accounts.filter(a => a.id !== accountId);
                    },
                    error: (err) => {
                        console.error('Delete error:', err);
                        this.snackBar.open('Failed to disconnect account.', 'Close', { duration: 3000 });
                    }
                });
            }
        });
    }
}
