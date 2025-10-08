import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ProductIngestion } from './product-ingestion';

const routes: Routes = [{ path: '', component: ProductIngestion }];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProductIngestionRoutingModule { }
