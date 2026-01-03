import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TranslocoService, TranslocoModule } from '@ngneat/transloco';

import { MaterialModule } from '../../../shared/material.module';
import { IntegrationsTabComponent } from '../tabs/integrations-tab.component';
import { MarketingTabComponent } from '../tabs/marketing-tab.component';
import { InventoryTabComponent } from '../tabs/inventory-tab.component';
import { DataTabComponent } from '../tabs/data-tab.component';
import { AiTabComponent } from '../tabs/ai-tab.component';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.html',
  styleUrl: './settings.scss',
  standalone: true,
  imports: [
    MaterialModule,
    TranslocoModule,
    IntegrationsTabComponent,
    MarketingTabComponent,
    InventoryTabComponent,
    DataTabComponent,
    AiTabComponent
  ],
})

export class Settings implements OnInit {
  constructor() { }
  ngOnInit(): void { }
}
