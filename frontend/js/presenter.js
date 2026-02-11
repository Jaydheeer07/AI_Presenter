/**
 * DexIQ AI Presenter — WebSocket client, slide control, and audio playback.
 *
 * Connects to the FastAPI backend via WebSocket and receives commands to
 * control Reveal.js slides, play audio, and manage the avatar.
 */

(function () {
    'use strict';

    // --- Configuration ---
    const WS_URL = `ws://${window.location.host}/ws/presenter`;
    const RECONNECT_DELAY = 3000;

    // --- DOM Elements ---
    const audioPlayer = document.getElementById('audio-player');
    const avatarEl = document.getElementById('avatar');
    const avatarContainer = document.getElementById('avatar-container');
    const questionOverlay = document.getElementById('question-overlay');
    const questionTarget = document.getElementById('question-target');
    const questionText = document.getElementById('question-text');
    const responseOverlay = document.getElementById('response-overlay');
    const responseText = document.getElementById('response-text');
    const qaUrl = document.getElementById('qa-url');

    // Set Q&A URL
    if (qaUrl) {
        qaUrl.textContent = `${window.location.origin}/static/ask.html`;
    }

    // --- WebSocket Connection ---
    let ws = null;
    let reconnectTimer = null;

    function connect() {
        if (ws && ws.readyState === WebSocket.OPEN) return;

        ws = new WebSocket(WS_URL);

        ws.onopen = function () {
            console.log('[Presenter] Connected to backend.');
            clearTimeout(reconnectTimer);
        };

        ws.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('[Presenter] Failed to parse message:', e);
            }
        };

        ws.onclose = function () {
            console.warn('[Presenter] Disconnected. Reconnecting...');
            reconnectTimer = setTimeout(connect, RECONNECT_DELAY);
        };

        ws.onerror = function (err) {
            console.error('[Presenter] WebSocket error:', err);
        };
    }

    function sendToBackend(type, data) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type, data }));
        }
    }

    // --- Message Handler ---
    function handleMessage(msg) {
        const { type, data } = msg;

        switch (type) {
            case 'connected':
                console.log('[Presenter]', data.message);
                break;

            case 'advance_slide':
                Reveal.next();
                break;

            case 'goto_slide':
                Reveal.slide(data.slideIndex || 0);
                break;

            case 'play_audio':
                playPreGenAudio(data.audioUrl, data.fallback);
                break;

            case 'play_live_audio':
                playLiveAudio(data.audioData, data.responseText);
                break;

            case 'show_question':
                showQuestion(data.targetName, data.question);
                break;

            case 'show_response_text':
                showResponseText(data.text);
                break;

            case 'show_avatar':
                setAvatarMode(data.mode);
                break;

            case 'hide_avatar':
                setAvatarMode('idle');
                break;

            case 'pause':
                pauseAll();
                break;

            case 'status':
                console.log('[Presenter] Status:', data);
                break;

            case 'pong':
                break;

            default:
                console.log('[Presenter] Unknown message type:', type, data);
        }
    }

    // --- Audio Playback ---

    function playPreGenAudio(audioUrl, fallback) {
        hideOverlays();

        audioPlayer.src = audioUrl;
        audioPlayer.load();

        const playPromise = audioPlayer.play();
        if (playPromise !== undefined) {
            playPromise.catch(function (err) {
                console.warn('[Presenter] Audio play failed:', err);
                if (fallback) {
                    console.log('[Presenter] Audio file not found, continuing without audio.');
                }
                // Notify backend that audio "ended" even if it failed
                sendToBackend('audio_ended', {});
            });
        }
    }

    function playLiveAudio(audioBase64, text) {
        hideOverlays();

        if (text) {
            showResponseText(text);
        }

        // Decode base64 audio and play
        const audioBytes = Uint8Array.from(atob(audioBase64), function (c) {
            return c.charCodeAt(0);
        });
        const blob = new Blob([audioBytes], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);

        audioPlayer.src = url;
        audioPlayer.load();

        audioPlayer.play().catch(function (err) {
            console.warn('[Presenter] Live audio play failed:', err);
            sendToBackend('audio_ended', {});
        });

        // Clean up object URL after playback
        audioPlayer.onended = function () {
            URL.revokeObjectURL(url);
        };
    }

    // Audio ended event — notify backend
    audioPlayer.addEventListener('ended', function () {
        setAvatarMode('idle');
        hideOverlays();
        sendToBackend('audio_ended', {});
    });

    // --- Avatar Control ---

    function setAvatarMode(mode) {
        // Remove all state classes
        avatarEl.className = 'avatar';

        switch (mode) {
            case 'speaking':
                avatarEl.classList.add('avatar-speaking');
                avatarContainer.classList.remove('expanded');
                break;

            case 'speaking_live':
                avatarEl.classList.add('avatar-speaking-live');
                avatarContainer.classList.add('expanded');
                break;

            case 'thinking':
                avatarEl.classList.add('avatar-thinking');
                avatarContainer.classList.remove('expanded');
                break;

            case 'listening':
                avatarEl.classList.add('avatar-listening');
                avatarContainer.classList.remove('expanded');
                break;

            case 'idle':
            default:
                avatarEl.classList.add('avatar-idle');
                avatarContainer.classList.remove('expanded');
                break;
        }
    }

    // --- Audio-Reactive Avatar ---
    let audioContext = null;
    let analyser = null;
    let animationId = null;

    function initAudioReactive() {
        if (audioContext) return;

        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;

            const source = audioContext.createMediaElementSource(audioPlayer);
            source.connect(analyser);
            analyser.connect(audioContext.destination);

            animateAvatar();
        } catch (e) {
            console.warn('[Presenter] Web Audio API not available:', e);
        }
    }

    function animateAvatar() {
        if (!analyser) return;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);

        // Calculate average volume
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const average = sum / dataArray.length;

        // Scale avatar based on audio volume
        const scale = 1 + (average / 512);
        const ring = avatarEl.querySelector('.avatar-ring');
        const core = avatarEl.querySelector('.avatar-core');

        if (ring && audioPlayer && !audioPlayer.paused) {
            ring.style.transform = `scale(${scale})`;
            core.style.transform = `scale(${0.9 + average / 600})`;
        }

        animationId = requestAnimationFrame(animateAvatar);
    }

    // Initialize audio context on first user interaction (browser requirement)
    document.addEventListener('click', function () {
        initAudioReactive();
    }, { once: true });

    // Also try on first audio play
    audioPlayer.addEventListener('play', function () {
        initAudioReactive();
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }
    });

    // --- Overlays ---

    function showQuestion(targetName, question) {
        questionTarget.textContent = targetName ? `Question for ${targetName}:` : 'Question:';
        questionText.textContent = question;
        questionOverlay.classList.remove('hidden');
        responseOverlay.classList.add('hidden');
    }

    function showResponseText(text) {
        responseText.textContent = text;
        responseOverlay.classList.remove('hidden');
        questionOverlay.classList.add('hidden');
    }

    function hideOverlays() {
        questionOverlay.classList.add('hidden');
        responseOverlay.classList.add('hidden');
    }

    function pauseAll() {
        audioPlayer.pause();
        setAvatarMode('idle');
        hideOverlays();
    }

    // --- Heartbeat ---
    setInterval(function () {
        sendToBackend('ping', {});
    }, 30000);

    // --- Slide change tracking ---
    Reveal.on('slidechanged', function (event) {
        sendToBackend('slide_changed', { slideIndex: event.indexh });
    });

    // --- Initialize ---
    connect();

})();
