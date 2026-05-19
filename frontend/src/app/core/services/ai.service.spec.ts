import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';

import { AiService } from './ai.service';
import { environment } from '../../../environments/environment';

describe('AiService', () => {
    let service: AiService;
    let httpMock: HttpTestingController;
    const capabilitiesUrl = `${environment.apiUrl}/ai/capabilities`;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
        });
        service = TestBed.inject(AiService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it('getCapabilities() caches the response across multiple subscribers', async () => {
        const payload = { ready: true, enabled: true, configured: true, provider: 'google' };

        const first$ = service.getCapabilities();
        const firstPromise = firstValueFrom(first$);

        // Second subscribe must not trigger a second HTTP request (shareReplay).
        const secondPromise = firstValueFrom(service.getCapabilities());

        const req = httpMock.expectOne(capabilitiesUrl);
        expect(req.request.method).toBe('GET');
        req.flush(payload);
        // expectOne also verifies no extra request exists.

        expect(await firstPromise).toEqual(payload);
        expect(await secondPromise).toEqual(payload);
    });

    it('isReady$() reflects the cached capabilities ready flag', async () => {
        const readyPromise = firstValueFrom(service.isReady$());
        httpMock.expectOne(capabilitiesUrl).flush({ ready: false, enabled: false, configured: false, provider: 'google' });
        expect(await readyPromise).toBe(false);
    });

    it('returns the disabled-default shape when /capabilities errors', async () => {
        const caps$ = firstValueFrom(service.getCapabilities());
        httpMock.expectOne(capabilitiesUrl).error(new ProgressEvent('network'));
        expect(await caps$).toEqual({ ready: false, enabled: false, configured: false, provider: null });
    });

    it('invalidateCapabilities() forces a re-fetch on next subscribe', async () => {
        const primed = firstValueFrom(service.getCapabilities());
        httpMock.expectOne(capabilitiesUrl).flush({ ready: true, enabled: true, configured: true, provider: 'google' });
        expect((await primed).ready).toBe(true);

        service.invalidateCapabilities();

        const refetched = firstValueFrom(service.getCapabilities());
        httpMock.expectOne(capabilitiesUrl).flush({ ready: false, enabled: false, configured: false, provider: 'openai' });
        expect((await refetched).ready).toBe(false);
    });
});
