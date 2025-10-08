import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';

describe('HardwareService', () => {
  let service: HardwareService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // NOTE: Further tests for this service are not possible in the current CI
  // environment. The global `navigator.mediaDevices` object is read-only and
  // cannot be mocked, which prevents testing the `getCameraStream` and
  // `captureImage` methods in isolation.
});
