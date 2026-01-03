import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ProductIngestion } from './product-ingestion';
import { TranslocoTestingModule } from '@ngneat/transloco';

describe('ProductIngestion', () => {
  let component: ProductIngestion;
  let fixture: ComponentFixture<ProductIngestion>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ProductIngestion,
        HttpClientTestingModule,
        TranslocoTestingModule.forRoot({
          langs: { en: {}, 'es-MX': {} },
          translocoConfig: { availableLangs: ['en', 'es-MX'], defaultLang: 'en' }
        })
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ProductIngestion);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
