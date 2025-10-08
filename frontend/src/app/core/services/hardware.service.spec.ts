import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';
import { firstValueFrom } from 'rxjs';

describe('HardwareService', () => {
  let service: HardwareService;
  let getUserMediaSpy: jasmine.Spy;
  let originalGetUserMedia: any;

  beforeEach(() => {
    // Ensure the global object exists before we try to modify it
    if (!navigator.mediaDevices) {
      (navigator as any).mediaDevices = {};
    }

    // Store the original function so we can restore it later
    originalGetUserMedia = navigator.mediaDevices.getUserMedia;

    // Create a spy and overwrite the original function completely
    getUserMediaSpy = jasmine.createSpy('getUserMediaSpy');
    (navigator.mediaDevices as any).getUserMedia = getUserMediaSpy;

    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
  });

  afterEach(() => {
    // Restore the original function after each test to avoid side-effects
    (navigator.mediaDevices as any).getUserMedia = originalGetUserMedia;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should request camera stream', async () => {
    const mockStream = {} as MediaStream;
    getUserMediaSpy.and.returnValue(Promise.resolve(mockStream));

    const stream = await firstValueFrom(service.getCameraStream());

    expect(stream).toBe(mockStream);
    expect(getUserMediaSpy).toHaveBeenCalledWith({
      video: { facingMode: 'environment' },
    });
  });

  it('should handle camera access denial', async () => {
    const mockError = new Error('Permission denied');
    getUserMediaSpy.and.returnValue(Promise.reject(mockError));

    await expectAsync(firstValueFrom(service.getCameraStream())).toBeRejectedWith(mockError);
  });
});
