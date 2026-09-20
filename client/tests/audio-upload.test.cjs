const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');

// Run Expo's installed multipart implementation, without a phone runtime.
function loadTs(filename, overrides = {}, globals = {}) {
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  const localRequire = (name) => {
    if (name in overrides) return overrides[name];
    if (name.startsWith('.')) return loadTs(path.resolve(path.dirname(filename), `${name}.ts`), overrides, globals);
    return require(name);
  };
  vm.runInNewContext(code, {
    module, exports: module.exports, require: localRequire,
    Blob, TextEncoder, Uint8Array, AbortController, setTimeout, clearTimeout,
    ...globals,
  }, { filename });
  return module.exports;
}

const { convertFormDataAsync } = loadTs(path.join(root, 'node_modules/expo/src/winter/fetch/convertFormData.ts'));
const { installFormDataPatch } = loadTs(path.join(root, 'node_modules/expo/src/winter/FormData.ts'));
class NativeFormData { constructor() { this._parts = []; } }
const FormData = installFormDataPatch(NativeFormData);

test('Expo rejects legacy URI parts with the reported error', async () => {
  const form = new FormData();
  form.append('audio', { uri: 'file:///recording.wav', name: 'recording.wav', type: 'audio/wav' });
  await assert.rejects(convertFormDataAsync(form), /Unsupported FormDataPart implementation/);
});

test('native recording upload serializes file bytes and private routing fields', async () => {
  class NativeFile {
    constructor(uri) { this.uri = uri; this.name = 'recording.wav'; this.type = 'audio/wav'; }
    async bytes() { return new TextEncoder().encode('RIFF-audio-bytes'); }
  }
  const { postRoomAudio } = loadTs(path.join(root, 'src/http.ts'), {
    'expo-file-system': { File: NativeFile },
  }, {
    FormData,
    fetch: async (url, request) => {
      assert.equal(url, 'http://localhost:8000/rooms/test/audio');
      const { body } = await convertFormDataAsync(request.body);
      const multipart = new TextDecoder().decode(body);
      assert.match(multipart, /name="speaker"\r\n\r\nsam/);
      assert.match(multipart, /name="visibility"\r\n\r\nprivate:sam/);
      assert.match(multipart, /name="audio"; filename="recording.wav"/);
      assert.match(multipart, /RIFF-audio-bytes/);
      assert.doesNotMatch(multipart, /name="transcript"/);
      return { ok: true, json: async () => ({ text: 'My budget is $150', stt: 'muse' }) };
    },
  });
  const result = await postRoomAudio('localhost:8000', 'test', 'sam', 'private:sam', 'file:///recording.wav');
  assert.equal(result.stt, 'muse');
});
