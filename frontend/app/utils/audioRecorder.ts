/**
 * Cross-browser resilient microphone capture and audio recording utility.
 *
 * Handles:
 * - Insecure context detection (HTTP on LAN vs localhost vs HTTPS).
 * - Hardware constraint auto-fallback (prevent OverconstrainedError).
 * - Legacy getUserMedia polyfill.
 * - MediaRecorder with MIME cascade.
 * - Web Audio API (AudioContext) WAV encoder fallback if MediaRecorder is unavailable.
 */

export class VoiceRecordingError extends Error {
  code: string;
  originalError?: any;

  constructor(code: string, message: string, originalError?: any) {
    super(message);
    this.name = 'VoiceRecordingError';
    this.code = code;
    this.originalError = originalError;
  }
}

/**
 * Checks whether the current window origin is a secure context.
 * Browsers block navigator.mediaDevices in insecure contexts (plain HTTP on non-localhost IPs).
 */
export function isSecureOrigin(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.isSecureContext) return true;
  const hostname = window.location.hostname;
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]';
}

/**
 * Acquires a microphone MediaStream with graceful constraint degradation.
 */
export async function getMicrophoneStream(): Promise<MediaStream> {
  if (typeof window === 'undefined') {
    throw new VoiceRecordingError('UNSUPPORTED_BROWSER', 'Window is not defined');
  }

  if (!isSecureOrigin()) {
    throw new VoiceRecordingError(
      'INSECURE_CONTEXT',
      'Microphone access requires HTTPS or accessing via http://localhost:3000'
    );
  }

  // Resolve getUserMedia across modern and legacy prefixes
  const nav = navigator as any;
  const getUserMediaFn =
    navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices) ||
    nav.getUserMedia?.bind(nav) ||
    nav.webkitGetUserMedia?.bind(nav) ||
    nav.mozGetUserMedia?.bind(nav) ||
    nav.msGetUserMedia?.bind(nav);

  if (!getUserMediaFn) {
    throw new VoiceRecordingError(
      'UNSUPPORTED_BROWSER',
      'getUserMedia is not supported by this browser'
    );
  }

  // Attempt 1: Universal unconstrained audio stream (maximum compatibility across all hardware/drivers)
  try {
    return await getUserMediaFn({ audio: true });
  } catch (err: any) {
    // Attempt 2: Retry with explicit processing flags if basic failed
    try {
      return await getUserMediaFn({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (retryErr: any) {
      throw normalizeMediaError(err || retryErr);
    }
  }
}

function normalizeMediaError(err: any): VoiceRecordingError {
  const name = err?.name || '';
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return new VoiceRecordingError('PERMISSION_DENIED', 'Microphone permission denied', err);
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return new VoiceRecordingError('NO_DEVICE_FOUND', 'No microphone hardware found', err);
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return new VoiceRecordingError('DEVICE_BUSY', 'Microphone is busy or blocked', err);
  }
  if (name === 'SecurityError') {
    return new VoiceRecordingError('INSECURE_CONTEXT', 'Security error accessing microphone', err);
  }
  return new VoiceRecordingError('UNKNOWN_ERROR', err?.message || 'Failed to access microphone', err);
}

export interface VoiceRecorderSession {
  stop: () => Promise<Blob>;
  cancel: () => void;
  stream: MediaStream;
}

/**
 * Creates a voice recorder session that works across all modern and legacy browsers.
 */
export function startVoiceRecordingSession(stream: MediaStream): VoiceRecorderSession {
  // Option A: MediaRecorder available
  if (typeof MediaRecorder !== 'undefined') {
    let mimeType = '';
    const candidateTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg',
      'audio/wav',
    ];

    for (const type of candidateTypes) {
      if (typeof MediaRecorder.isTypeSupported === 'function' && MediaRecorder.isTypeSupported(type)) {
        mimeType = type;
        break;
      }
    }

    try {
      const chunks: Blob[] = [];
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.start(250);

      let isCancelled = false;

      return {
        stream,
        cancel: () => {
          isCancelled = true;
          if (recorder.state !== 'inactive') {
            try {
              recorder.stop();
            } catch {}
          }
          stream.getTracks().forEach((track) => track.stop());
        },
        stop: () => {
          return new Promise<Blob>((resolve) => {
            recorder.onstop = () => {
              stream.getTracks().forEach((track) => track.stop());
              if (isCancelled || chunks.length === 0) {
                resolve(new Blob([], { type: recorder.mimeType || 'audio/webm' }));
                return;
              }
              const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
              resolve(blob);
            };
            if (recorder.state !== 'inactive') {
              recorder.stop();
            }
          });
        },
      };
    } catch {
      // Fall through to Web Audio API fallback if MediaRecorder constructor threw
    }
  }

  // Option B: Web Audio API (AudioContext) Fallback
  return startAudioContextRecorder(stream);
}

/**
 * Web Audio API fallback for browsers lacking MediaRecorder or with strict restrictions.
 * Direct captures PCM Float32 and encodes into 16-bit PCM WAV.
 */
function startAudioContextRecorder(stream: MediaStream): VoiceRecorderSession {
  const AudioContextClass =
    (typeof window !== 'undefined' && (window.AudioContext || (window as any).webkitAudioContext)) || null;

  if (!AudioContextClass) {
    throw new VoiceRecordingError(
      'UNSUPPORTED_BROWSER',
      'Neither MediaRecorder nor AudioContext is supported'
    );
  }

  const audioCtx: AudioContext = new AudioContextClass();
  const source = audioCtx.createMediaStreamSource(stream);
  const bufferSize = 4096;
  const scriptNode = audioCtx.createScriptProcessor(bufferSize, 1, 1);
  const audioChunks: Float32Array[] = [];
  let isCancelled = false;

  scriptNode.onaudioprocess = (e) => {
    if (isCancelled) return;
    const channelData = e.inputBuffer.getChannelData(0);
    audioChunks.push(new Float32Array(channelData));
  };

  source.connect(scriptNode);
  scriptNode.connect(audioCtx.destination);

  return {
    stream,
    cancel: () => {
      isCancelled = true;
      try {
        source.disconnect();
        scriptNode.disconnect();
        audioCtx.close();
      } catch {}
      stream.getTracks().forEach((track) => track.stop());
    },
    stop: async () => {
      try {
        source.disconnect();
        scriptNode.disconnect();
        await audioCtx.close();
      } catch {}
      stream.getTracks().forEach((track) => track.stop());

      if (isCancelled || audioChunks.length === 0) {
        return new Blob([], { type: 'audio/wav' });
      }

      return encodePcmToWav(audioChunks, audioCtx.sampleRate);
    },
  };
}

/**
 * Encodes array of Float32 audio chunks into a standard 16-bit PCM WAV Blob.
 */
function encodePcmToWav(chunks: Float32Array[], inputSampleRate: number): Blob {
  let totalLength = 0;
  for (const chunk of chunks) totalLength += chunk.length;

  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  const targetSampleRate = 16000;
  const resampled = downsampleBuffer(merged, inputSampleRate, targetSampleRate);

  const numChannels = 1;
  const bytesPerSample = 2; // 16-bit
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = targetSampleRate * blockAlign;
  const dataByteLength = resampled.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataByteLength);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataByteLength, true);
  writeString(view, 8, 'WAVE');

  // fmt subchunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, targetSampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true); // BitsPerSample

  // data subchunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataByteLength, true);

  // Write PCM 16-bit samples
  let sampleIndex = 0;
  let fileOffset = 44;
  while (sampleIndex < resampled.length) {
    const s = Math.max(-1, Math.min(1, resampled[sampleIndex]));
    view.setInt16(fileOffset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    sampleIndex++;
    fileOffset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function downsampleBuffer(buffer: Float32Array, inputRate: number, outputRate: number): Float32Array {
  if (inputRate === outputRate) return buffer;
  if (inputRate < outputRate) return buffer;

  const ratio = inputRate / outputRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

/**
 * Returns user-friendly, localized error messages based on error code.
 */
export function resolveVoiceErrorMessage(
  err: any,
  t: (key: string) => string
): string {
  const code = err instanceof VoiceRecordingError ? err.code : err?.name || '';

  if (code === 'INSECURE_CONTEXT' || code === 'SecurityError') {
    return t('advisor.voice_insecure_context');
  }
  if (code === 'PERMISSION_DENIED' || code === 'NotAllowedError' || code === 'PermissionDeniedError') {
    return t('advisor.voice_mic_denied');
  }
  if (code === 'NO_DEVICE_FOUND' || code === 'NotFoundError' || code === 'DevicesNotFoundError') {
    return t('advisor.voice_no_mic');
  }
  if (code === 'DEVICE_BUSY' || code === 'NotReadableError' || code === 'TrackStartError') {
    return t('advisor.voice_mic_busy');
  }

  return t('advisor.voice_unsupported_browser');
}
