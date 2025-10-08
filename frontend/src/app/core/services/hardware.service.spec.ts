import { TestBed } from '@angular/core/testing';
import { HardwareService } from './hardware.service';

describe('HardwareService', () => {
  let service: HardwareService;
  let getUserMediaSpy: jasmine.Spy;

  beforeEach(() => {
    // In some test environments (especially headless ones), navigator.mediaDevices might not exist.
    // We create a dummy object to ensure the spy can be attached.
    if (!navigator.mediaDevices) {
      (navigator as any).mediaDevices = {};
    }

    TestBed.configureTestingModule({});
    service = TestBed.inject(HardwareService);
    // Spy on the method for all tests in this block
    getUserMediaSpy = spyOn(navigator.mediaDevices, 'getUserMedia');
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should request camera stream', async () => {
    const mockStream = {} as MediaStream;
    getUserMediaSpy.and.returnValue(Promise.resolve(mockStream));

    const stream = await service.getCameraStream().toPromise();
    
    expect(stream).toBe(mockStream);
    expect(getUserMediaSpy).toHaveBeenCalledWith({
      video: { facingMode: 'environment' },
    });
  });

  it('should handle camera access denial', async () => {
    const mockError = new Error('Permission denied');
    getUserMediaSpy.and.returnValue(Promise.reject(mockError));

    await expectAsync(service.getCameraStream().toPromise()).toBeRejectedWith(mockError);
  });
});
