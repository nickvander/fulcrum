import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxScannerQrcodeModule } from 'ngx-scanner-qrcode';

import { ProductIngestionRoutingModule } from './product-ingestion-routing-module';
import { ProductIngestion } from './product-ingestion';
import { SharedModule } from '../../shared/shared-module';


@NgModule({
  declarations: [
    ProductIngestion
  ],
  imports: [
    CommonModule,
    ProductIngestionRoutingModule,
    NgxScannerQrcodeModule,
    SharedModule,
  ]
})
export class ProductIngestionModule { }