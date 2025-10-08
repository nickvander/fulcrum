import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';
import { firstValueFrom } from 'rxjs';

describe('HardwareService', () => {
  let service: HardwareService;
  let getUserMediaSpy: jasmine.Spy;

  beforeEach(() => {
    // In headless CI environments, navigator.mediaDevices or getUserMedia might not exist.
    // We create a dummy object/function to ensure the spy can always be attached.
    if (!navigator.mediaDevices) {
      (navigator as any).mediaDevices = {};
    }
    if (!navigator.mediaDevices.getUserMedia) {
      (navigator.mediaDevices as any).getUserMedia = async () => new MediaStream();
    }

    // Spy on the method BEFORE TestBed is configured to guarantee it's mocked.
    getUserMediaSpy = spyOn(navigator.mediaDevices, 'getUserMedia');

    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
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
