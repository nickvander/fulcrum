
import { HttpClient } from '@angular/common/http';
import {
    TRANSLOCO_LOADER,
    Translation,
    TranslocoLoader,
    TRANSLOCO_CONFIG,
    translocoConfig,
    TranslocoModule,
    TRANSLOCO_TRANSPILER,
    DefaultTranspiler,
    TRANSLOCO_MISSING_HANDLER,
    TranslocoMissingHandler,
    TRANSLOCO_FALLBACK_STRATEGY,
    DefaultFallbackStrategy,
    TRANSLOCO_INTERCEPTOR,
    TranslocoInterceptor
} from '@ngneat/transloco';
import { Injectable, NgModule, isDevMode } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TranslocoHttpLoader implements TranslocoLoader {
    constructor(private http: HttpClient) { }

    getTranslation(lang: string) {
        return this.http.get<Translation>(`/assets/i18n/${lang}.json`);
    }
}

// Default missing handler - logs missing keys in dev mode
@Injectable({ providedIn: 'root' })
export class CustomMissingHandler implements TranslocoMissingHandler {
    handle(key: string) {
        if (!isDevMode()) return key;
        console.warn(`Missing translation for key: ${key}`);
        return key;
    }
}

// Default interceptor - no-op
@Injectable({ providedIn: 'root' })
export class CustomInterceptor implements TranslocoInterceptor {
    preSaveTranslation(translation: Translation, lang: string): Translation {
        return translation;
    }
    preSaveTranslationKey(key: string, value: string, lang: string): string {
        return value;
    }
}

@NgModule({
    exports: [TranslocoModule],
    providers: [
        {
            provide: TRANSLOCO_CONFIG,
            useValue: translocoConfig({
                availableLangs: ['en', 'es-MX'],
                defaultLang: 'en',
                reRenderOnLangChange: true,
                prodMode: !isDevMode(),
            })
        },
        { provide: TRANSLOCO_LOADER, useClass: TranslocoHttpLoader },
        { provide: TRANSLOCO_TRANSPILER, useClass: DefaultTranspiler },
        { provide: TRANSLOCO_MISSING_HANDLER, useClass: CustomMissingHandler },
        { provide: TRANSLOCO_FALLBACK_STRATEGY, useClass: DefaultFallbackStrategy },
        { provide: TRANSLOCO_INTERCEPTOR, useClass: CustomInterceptor }
    ]
})
export class TranslocoRootModule { }


