import assert from 'node:assert';

// Simulating the FormData construction logic from Launch.jsx
function buildLaunchFormData({ file, metadata, settings, confidenceTouched }) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('latitude', String(metadata.latitude));
  formData.append('longitude', String(metadata.longitude));
  formData.append('sonar_type', metadata.sonarType);
  formData.append('resolution', metadata.resolution);
  formData.append('depth_min', String(metadata.depthMin));
  formData.append('depth_max', String(metadata.depthMax));
  if (confidenceTouched) {
    formData.append('confidence_threshold', String(settings.confidence));
  }
  formData.append('selected_classes', settings.selected.join(','));
  formData.append('min_object_size', '10');
  return formData;
}

const mockFile = new Blob(['mock binary data'], { type: 'image/jpeg' });
const mockMetadata = {
  latitude: 13.0628,
  longitude: 80.3582,
  sonarType: 'Side-Scan',
  resolution: '0.5 m/px',
  depthMin: 4,
  depthMax: 38,
};

// 1. Initial untouched state (default confidence = 20)
let confidenceTouched = false;
let settings = {
  confidence: 20,
  selected: ['Debris', 'Shipwreck', 'Rocks', 'Other'],
};

const fd1 = buildLaunchFormData({
  file: mockFile,
  metadata: mockMetadata,
  settings,
  confidenceTouched,
});

assert.strictEqual(
  fd1.has('confidence_threshold'),
  false,
  'FormData MUST omit confidence_threshold before slider interaction'
);
assert.strictEqual(fd1.get('min_object_size'), '10');
assert.strictEqual(fd1.get('selected_classes'), 'Debris,Shipwreck,Rocks,Other');
console.log('PASS: FormData omits confidence_threshold before slider interaction.');

// 2. User moves slider to 45
confidenceTouched = true;
settings.confidence = 45;

const fd2 = buildLaunchFormData({
  file: mockFile,
  metadata: mockMetadata,
  settings,
  confidenceTouched,
});

assert.strictEqual(
  fd2.has('confidence_threshold'),
  true,
  'FormData MUST include confidence_threshold after slider interaction'
);
assert.strictEqual(fd2.get('confidence_threshold'), '45');
console.log('PASS: FormData includes confidence_threshold when slider is set to 45.');

// 3. User moves slider back to initial 20
settings.confidence = 20;

const fd3 = buildLaunchFormData({
  file: mockFile,
  metadata: mockMetadata,
  settings,
  confidenceTouched,
});

assert.strictEqual(
  fd3.has('confidence_threshold'),
  true,
  'FormData MUST include confidence_threshold even if returned to 20'
);
assert.strictEqual(fd3.get('confidence_threshold'), '20');
console.log('PASS: FormData includes confidence_threshold="20" when returned to 20.');
