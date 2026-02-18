/**
 * ARIA AI Presenter — WebSocket client, slide control, and audio playback.
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
                gotoSlideAndRevealFragments(data.slideIndex || 0);
                break;

            case 'play_audio':
                playPreGenAudio(data.audioUrl, data.fallback);
                break;

            case 'play_live_audio':
                playLiveAudio(data.audioData, data.responseText);
                break;

            case 'stream_audio_start':
                startStreamingAudio(data.responseText);
                break;

            case 'audio_chunk':
                handleAudioChunk(data);
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

            case 'stop_audio':
                stopAudio();
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

    // --- Slide Navigation ---

    /**
     * Navigate to a slide and immediately reveal all fragments on it.
     * Reveal.slide() alone leaves fragments at opacity:0 — they only appear
     * when stepping through with Reveal.next(). Since the backend jumps
     * directly to slides, we need to force-show all fragments so the
     * audience sees the full slide content at once.
     */
    function gotoSlideAndRevealFragments(slideIndex) {
        // Navigate to the target slide
        Reveal.slide(slideIndex, 0, 0);

        // Small delay to let Reveal.js finish its slide transition and DOM update
        setTimeout(function () {
            // Get the current slide element
            var currentSlide = Reveal.getCurrentSlide();
            if (currentSlide) {
                // Find all fragment elements on this slide and mark them as visible
                var fragments = currentSlide.querySelectorAll('.fragment');
                for (var i = 0; i < fragments.length; i++) {
                    fragments[i].classList.add('visible');
                }
            }
        }, 100);
    }

    // --- Audio Playback ---

    function playPreGenAudio(audioUrl, fallback) {
        hideOverlays();

        const separator = audioUrl.indexOf('?') >= 0 ? '&' : '?';
        const cacheBustedUrl = `${audioUrl}${separator}v=${Date.now()}`;

        audioPlayer.src = cacheBustedUrl;
        audioPlayer.load();

        const playPromise = audioPlayer.play();
        if (playPromise !== undefined) {
            playPromise.catch(function (err) {
                console.warn('[Presenter] Audio play failed:', err);
                if (fallback) {
                    console.log('[Presenter] Audio file missing, continuing without audio.');
                }
                // Notify backend that audio "ended" even if it failed
                sendToBackend('audio_ended', { error: 'play_failed' });
            });
        }
    }

    // Handle HTTP 404 for missing pre-gen audio files
    audioPlayer.addEventListener('error', function () {
        var error = audioPlayer.error;
        if (error) {
            console.warn('[Presenter] Audio error:', error.code, error.message);
        }
        // Notify backend so the state machine can continue
        sendToBackend('audio_ended', { error: 'load_error' });
    });

    function playLiveAudio(audioBase64, text) {
        hideOverlays();

        if (text) {
            showResponseText(text);
        }

        // Decode base64 audio and play
        var audioBytes = Uint8Array.from(atob(audioBase64), function (c) {
            return c.charCodeAt(0);
        });
        var blob = new Blob([audioBytes], { type: 'audio/mpeg' });
        var url = URL.createObjectURL(blob);

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

    // --- Streaming Audio Playback ---
    // Buffers audio chunks from the backend and plays them as they arrive.
    // Uses a simple approach: collect all chunks, then play once complete.
    // (MediaSource Extensions are unreliable for MP3 across browsers.)

    var streamBuffer = [];
    var isStreaming = false;
    var streamResponseText = '';

    function startStreamingAudio(text) {
        console.log('[Presenter] Starting audio stream...');
        streamBuffer = [];
        isStreaming = true;
        streamResponseText = text || '';

        hideOverlays();
        if (text) {
            showResponseText(text);
        }
    }

    function handleAudioChunk(data) {
        if (!isStreaming) return;

        if (data.final) {
            // All chunks received — assemble and play
            console.log('[Presenter] Stream complete. Assembling ' + streamBuffer.length + ' chunks...');
            isStreaming = false;
            assembleAndPlayStream();
            return;
        }

        if (data.chunk) {
            // Decode base64 chunk and buffer it
            var raw = atob(data.chunk);
            var bytes = new Uint8Array(raw.length);
            for (var i = 0; i < raw.length; i++) {
                bytes[i] = raw.charCodeAt(i);
            }
            streamBuffer.push(bytes);
        }
    }

    function assembleAndPlayStream() {
        if (streamBuffer.length === 0) {
            console.warn('[Presenter] Empty stream buffer.');
            sendToBackend('audio_ended', {});
            return;
        }

        // Calculate total length
        var totalLength = 0;
        for (var i = 0; i < streamBuffer.length; i++) {
            totalLength += streamBuffer[i].length;
        }

        // Merge all chunks into one Uint8Array
        var merged = new Uint8Array(totalLength);
        var offset = 0;
        for (var j = 0; j < streamBuffer.length; j++) {
            merged.set(streamBuffer[j], offset);
            offset += streamBuffer[j].length;
        }

        console.log('[Presenter] Playing streamed audio: ' + totalLength + ' bytes from ' + streamBuffer.length + ' chunks');

        var blob = new Blob([merged], { type: 'audio/mpeg' });
        var url = URL.createObjectURL(blob);

        audioPlayer.src = url;
        audioPlayer.load();
        audioPlayer.play().catch(function (err) {
            console.warn('[Presenter] Streamed audio play failed:', err);
            sendToBackend('audio_ended', {});
        });

        audioPlayer.onended = function () {
            URL.revokeObjectURL(url);
        };

        streamBuffer = [];
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

    function stopAudio() {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        audioPlayer.src = '';
        setAvatarMode('idle');
        console.log('[Presenter] Audio stopped.');
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

        // Slide 9: start carousel auto-advance
        if (event.indexh === 9) {
            initCarousel();
        } else {
            stopCarousel();
        }

        // Slide 10: pause any playing music when leaving
        if (event.indexh !== 10) {
            pauseMusicPlayer();
        }
    });

    // --- Image Carousel (Slide 9) ---
    var carouselTimer = null;
    var carouselIndex = 0;

    function initCarousel() {
        var items = document.querySelectorAll('.carousel-item');
        var dots = document.querySelectorAll('.carousel-dot');
        if (!items.length) return;

        carouselIndex = 0;
        showCarouselItem(items, dots, carouselIndex);

        stopCarousel();
        carouselTimer = setInterval(function () {
            carouselIndex = (carouselIndex + 1) % items.length;
            showCarouselItem(items, dots, carouselIndex);
        }, 3500);

        // Dot click navigation
        dots.forEach(function (dot, i) {
            dot.onclick = function () {
                carouselIndex = i;
                showCarouselItem(items, dots, carouselIndex);
            };
        });
    }

    function showCarouselItem(items, dots, index) {
        items.forEach(function (item, i) {
            item.classList.toggle('active', i === index);
        });
        dots.forEach(function (dot, i) {
            dot.classList.toggle('active', i === index);
        });
    }

    function stopCarousel() {
        if (carouselTimer) {
            clearInterval(carouselTimer);
            carouselTimer = null;
        }
    }

    // --- Video Toggle (Slide 9) ---
    document.addEventListener('DOMContentLoaded', function () {
        var playBtn = document.querySelector('.video-play-btn');
        var aiVideo = document.querySelector('.ai-video');

        if (playBtn && aiVideo) {
            playBtn.addEventListener('click', function () {
                if (aiVideo.paused) {
                    aiVideo.play();
                    playBtn.textContent = '⏸ Pause';
                } else {
                    aiVideo.pause();
                    playBtn.textContent = '▶ Play';
                }
            });

            aiVideo.addEventListener('ended', function () {
                playBtn.textContent = '▶ Play';
            });
        }
    });

    // --- Music Player Toggle (Slide 10) ---
    var musicAudio = null;

    document.addEventListener('DOMContentLoaded', function () {
        var musicBtn = document.querySelector('.music-play-btn');
        var visualiser = document.querySelector('.music-visualiser');

        if (musicBtn) {
            musicBtn.addEventListener('click', function () {
                if (!musicAudio) {
                    musicAudio = new Audio('/audio/ai_music_sample.mp3');
                    musicAudio.addEventListener('ended', function () {
                        musicBtn.textContent = '▶ Play Sample';
                        if (visualiser) visualiser.classList.remove('playing');
                        musicAudio = null;
                    });
                }

                if (musicAudio.paused) {
                    musicAudio.play().catch(function (e) {
                        console.warn('[Presenter] Music play failed:', e);
                    });
                    musicBtn.textContent = '⏸ Pause';
                    if (visualiser) visualiser.classList.add('playing');
                } else {
                    musicAudio.pause();
                    musicBtn.textContent = '▶ Play Sample';
                    if (visualiser) visualiser.classList.remove('playing');
                }
            });
        }
    });

    function pauseMusicPlayer() {
        if (musicAudio && !musicAudio.paused) {
            musicAudio.pause();
            var musicBtn = document.querySelector('.music-play-btn');
            var visualiser = document.querySelector('.music-visualiser');
            if (musicBtn) musicBtn.textContent = '▶ Play Sample';
            if (visualiser) visualiser.classList.remove('playing');
        }
    }

    // --- Initialize ---
    connect();

})();
