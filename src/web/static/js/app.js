/**
 * MonsterBorg Mobile Web Interface JavaScript
 * Phase 1: Touch controls, WebSocket communication, virtual joystick
 *
 * See: docs/IMPLEMENTATION_PLAN.md
 */

(function() {
    'use strict';

    // =========================================================================
    // Configuration
    // =========================================================================
    const CONFIG = {
        CAMERA_REFRESH_RATE: 100,      // ms (10 fps)
        TELEMETRY_INTERVAL: 100,       // ms (10 Hz)
        JOYSTICK_UPDATE_RATE: 50,      // ms (20 Hz)
        HAPTIC_DURATION: 10,           // ms
        RECONNECT_DELAY: 2000,         // ms
        MAX_RECONNECT_ATTEMPTS: 10,
        DEAD_ZONE: 0.1,                // Joystick dead zone (0-1)
    };

    // =========================================================================
    // State
    // =========================================================================
    const state = {
        socket: null,
        connected: false,
        role: 'disconnected',      // 'controller', 'observer', 'disconnected'
        emergencyStop: false,
        speedMultiplier: 1.0,
        currentMode: 'buttons',    // 'buttons' or 'joystick'
        reconnectAttempts: 0,
        cameraInterval: null,
        joystickActive: false,
        joystickPosition: { x: 0, y: 0 },
        activeButtons: new Set(),
    };

    // =========================================================================
    // DOM Elements
    // =========================================================================
    let elements = {};

    function cacheElements() {
        elements = {
            // Status
            connectionStatus: document.getElementById('connection-status'),
            controlStatus: document.getElementById('control-status'),
            batteryStatus: document.getElementById('battery-status'),

            // Emergency
            emergencyBanner: document.getElementById('emergency-banner'),
            resetEmergency: document.getElementById('reset-emergency'),

            // Camera
            cameraContainer: document.getElementById('camera-container'),
            cameraFeed: document.getElementById('camera-feed'),
            fullscreenToggle: document.getElementById('fullscreen-toggle'),
            speedValue: document.getElementById('speed-value'),

            // Controls
            modeButtons: document.querySelectorAll('.mode-btn'),
            buttonControls: document.getElementById('button-controls'),
            joystickControls: document.getElementById('joystick-controls'),
            driveButtons: document.querySelectorAll('.drive-btn'),

            // Joystick
            joystickZone: document.getElementById('joystick-zone'),
            joystickBase: document.getElementById('joystick-base'),
            joystickStick: document.getElementById('joystick-stick'),

            // Speed
            speedSlider: document.getElementById('speed-slider'),
            speedLabel: document.getElementById('speed-label'),

            // Action buttons
            btnStop: document.getElementById('btn-stop'),
            btnEmergency: document.getElementById('btn-emergency'),
            btnPhoto: document.getElementById('btn-photo'),

            // Modal
            takeoverModal: document.getElementById('takeover-modal'),
            approveTakeover: document.getElementById('approve-takeover'),
            denyTakeover: document.getElementById('deny-takeover'),

            // Toast
            toastContainer: document.getElementById('toast-container'),

            // Cached sub-elements for performance (avoid querySelector in hot paths)
            batteryText: document.querySelector('#battery-status .battery-text'),
        };
    }

    // =========================================================================
    // Socket.IO Connection
    // =========================================================================
    function connectSocket() {
        if (state.socket && state.socket.connected) {
            return;
        }

        state.socket = io({
            reconnection: true,
            reconnectionAttempts: CONFIG.MAX_RECONNECT_ATTEMPTS,
            reconnectionDelay: CONFIG.RECONNECT_DELAY,
        });

        // Connection events
        state.socket.on('connect', handleConnect);
        state.socket.on('disconnect', handleDisconnect);
        state.socket.on('connect_error', handleConnectError);

        // Control events
        state.socket.on('control_status', handleControlStatus);
        state.socket.on('control_changed', handleControlChanged);
        state.socket.on('takeover_requested', handleTakeoverRequested);
        state.socket.on('takeover_pending', handleTakeoverPending);
        state.socket.on('takeover_denied', handleTakeoverDenied);

        // Emergency events
        state.socket.on('emergency_stop_active', handleEmergencyStopActive);
        state.socket.on('emergency_stop_cleared', handleEmergencyStopCleared);

        // Telemetry
        state.socket.on('telemetry', handleTelemetry);

        // Feedback
        state.socket.on('speed_updated', handleSpeedUpdated);
        state.socket.on('photo_saved', handlePhotoSaved);
        state.socket.on('error', handleServerError);
    }

    function handleConnect() {
        state.connected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus('connected', 'Connected');
        showToast('Connected to MonsterBorg', 'success');
        startCameraStream();
    }

    function handleDisconnect() {
        state.connected = false;
        state.role = 'disconnected';
        updateConnectionStatus('disconnected', 'Disconnected');
        updateControlStatus('--');
        stopCameraStream();
    }

    function handleConnectError(error) {
        state.reconnectAttempts++;
        console.error('Connection error:', error);
        updateConnectionStatus('disconnected', `Reconnecting (${state.reconnectAttempts})`);
    }

    function handleControlStatus(data) {
        state.role = data.role;
        updateControlStatus(data.role === 'controller' ? 'In Control' : 'Observing');
        if (data.message) {
            showToast(data.message, 'info');
        }
    }

    function handleControlChanged(data) {
        const isController = data.new_controller === state.socket.id;
        state.role = isController ? 'controller' : 'observer';
        updateControlStatus(isController ? 'In Control' : 'Observing');
        showToast(isController ? 'You now have control' : 'Control transferred', 'info');
    }

    function handleTakeoverRequested(data) {
        elements.takeoverModal.classList.remove('hidden');
        triggerHaptic();
    }

    function handleTakeoverPending(data) {
        showToast('Takeover request sent', 'info');
    }

    function handleTakeoverDenied(data) {
        showToast('Takeover request denied', 'warning');
    }

    function handleEmergencyStopActive(data) {
        state.emergencyStop = true;
        elements.emergencyBanner.classList.remove('hidden');
        triggerHaptic(100);
        showToast(`Emergency stop: ${data.reason}`, 'error');
    }

    function handleEmergencyStopCleared(data) {
        state.emergencyStop = false;
        elements.emergencyBanner.classList.add('hidden');
        showToast('Emergency stop cleared', 'success');
    }

    function handleTelemetry(data) {
        // Update battery display
        if (data.battery_voltage !== undefined) {
            const voltage = data.battery_voltage.toFixed(1);
            // Use cached batteryText element for performance (called at 10Hz)
            if (elements.batteryText) {
                elements.batteryText.textContent = `${voltage}V`;
            }

            // Update battery icon color based on level
            const batteryElement = elements.batteryStatus;
            if (data.battery_voltage < 10.5) {
                batteryElement.style.color = '#ff4444';
            } else if (data.battery_voltage < 11.0) {
                batteryElement.style.color = '#ffa500';
            } else {
                batteryElement.style.color = '#00c853';
            }
        }

        // Update speed display
        if (data.motor_left !== undefined && data.motor_right !== undefined) {
            const avgSpeed = Math.abs((data.motor_left + data.motor_right) / 2 * 100);
            elements.speedValue.textContent = Math.round(avgSpeed);
        }

        // Update emergency stop state
        if (data.emergency_stopped !== state.emergencyStop) {
            state.emergencyStop = data.emergency_stopped;
            if (state.emergencyStop) {
                elements.emergencyBanner.classList.remove('hidden');
            } else {
                elements.emergencyBanner.classList.add('hidden');
            }
        }
    }

    function handleSpeedUpdated(data) {
        state.speedMultiplier = data.speed;
        elements.speedSlider.value = data.speed * 100;
        elements.speedLabel.textContent = `${Math.round(data.speed * 100)}%`;
    }

    function handlePhotoSaved(data) {
        showToast(`Photo saved: ${data.filename}`, 'success');
        triggerHaptic();
    }

    function handleServerError(data) {
        showToast(data.message, 'error');
    }

    // =========================================================================
    // UI Updates
    // =========================================================================
    function updateConnectionStatus(status, text) {
        const dot = elements.connectionStatus.querySelector('.status-dot');
        const textEl = elements.connectionStatus.querySelector('.status-text');

        dot.className = 'status-dot ' + status;
        textEl.textContent = text;
    }

    function updateControlStatus(text) {
        elements.controlStatus.querySelector('.status-text').textContent = text;
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        elements.toastContainer.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // =========================================================================
    // Camera Stream
    // =========================================================================
    function startCameraStream() {
        if (state.cameraInterval) {
            return;
        }

        // Add error handler for failed image loads
        elements.cameraFeed.onerror = function() {
            // Don't show error toast for every frame - just log
            console.warn('Camera frame load failed');
        };

        // Track pending camera request to prevent pile-up
        let cameraRequestPending = false;

        // Load handler schedules next frame after current completes
        elements.cameraFeed.onload = function() {
            cameraRequestPending = false;
        };

        // Also clear pending on error to prevent getting stuck
        const originalOnError = elements.cameraFeed.onerror;
        elements.cameraFeed.onerror = function(e) {
            cameraRequestPending = false;
            if (originalOnError) originalOnError.call(this, e);
        };

        function refreshCamera() {
            // Only request new frame if previous request completed
            if (state.connected && !cameraRequestPending) {
                cameraRequestPending = true;
                elements.cameraFeed.src = '/cam.jpg?' + Date.now();
            }
        }

        state.cameraInterval = setInterval(refreshCamera, CONFIG.CAMERA_REFRESH_RATE);
        refreshCamera();
    }

    function stopCameraStream() {
        if (state.cameraInterval) {
            clearInterval(state.cameraInterval);
            state.cameraInterval = null;
        }
    }

    // =========================================================================
    // Motor Control
    // =========================================================================
    function sendDriveCommand(left, right) {
        if (!state.connected || state.role !== 'controller' || state.emergencyStop) {
            return;
        }

        state.socket.emit('drive', { left, right });
    }

    function sendJoystickCommand(x, y) {
        if (!state.connected || state.role !== 'controller' || state.emergencyStop) {
            return;
        }

        state.socket.emit('joystick', { x, y });
    }

    function sendStop() {
        if (state.connected) {
            state.socket.emit('stop');
        }
    }

    function sendEmergencyStop() {
        if (state.connected) {
            state.socket.emit('emergency_stop', { reason: 'User triggered' });
            triggerHaptic(100);
        }
    }

    function sendEmergencyReset() {
        if (state.connected) {
            state.socket.emit('emergency_reset');
        }
    }

    // =========================================================================
    // Touch Controls (Buttons)
    // =========================================================================
    function setupButtonControls() {
        elements.driveButtons.forEach(btn => {
            const left = parseFloat(btn.dataset.left);
            const right = parseFloat(btn.dataset.right);

            // Touch events for mobile
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                handleButtonPress(btn, left, right);
            }, { passive: false });

            btn.addEventListener('touchend', (e) => {
                e.preventDefault();
                handleButtonRelease(btn);
            }, { passive: false });

            btn.addEventListener('touchcancel', (e) => {
                e.preventDefault();
                handleButtonRelease(btn);
            }, { passive: false });

            // Mouse events for desktop
            btn.addEventListener('mousedown', (e) => {
                handleButtonPress(btn, left, right);
            });

            btn.addEventListener('mouseup', (e) => {
                handleButtonRelease(btn);
            });

            btn.addEventListener('mouseleave', (e) => {
                handleButtonRelease(btn);
            });
        });
    }

    function handleButtonPress(btn, left, right) {
        btn.classList.add('active');
        state.activeButtons.add(btn);
        sendDriveCommand(left, right);
        triggerHaptic();
    }

    function handleButtonRelease(btn) {
        btn.classList.remove('active');
        state.activeButtons.delete(btn);

        // Only stop if no buttons are pressed
        if (state.activeButtons.size === 0) {
            sendStop();
        }
    }

    // =========================================================================
    // Virtual Joystick
    // =========================================================================
    function setupJoystick() {
        const base = elements.joystickBase;
        const stick = elements.joystickStick;
        const zone = elements.joystickZone;

        let startTouch = null;
        let joystickInterval = null;

        function getJoystickBounds() {
            const baseRect = base.getBoundingClientRect();
            const stickRect = stick.getBoundingClientRect();
            const maxDistance = (baseRect.width - stickRect.width) / 2;
            return {
                centerX: baseRect.left + baseRect.width / 2,
                centerY: baseRect.top + baseRect.height / 2,
                maxDistance,
            };
        }

        function updateJoystickPosition(clientX, clientY) {
            const bounds = getJoystickBounds();

            // Calculate offset from center
            let dx = clientX - bounds.centerX;
            let dy = clientY - bounds.centerY;

            // Calculate distance from center
            const distance = Math.sqrt(dx * dx + dy * dy);

            // Clamp to max distance
            if (distance > bounds.maxDistance) {
                const scale = bounds.maxDistance / distance;
                dx *= scale;
                dy *= scale;
            }

            // Update stick position
            stick.style.transform = `translate(${dx}px, ${dy}px)`;

            // Normalize to -1 to 1
            const x = dx / bounds.maxDistance;
            const y = -dy / bounds.maxDistance; // Invert Y (up is positive)

            // Apply dead zone
            state.joystickPosition.x = Math.abs(x) < CONFIG.DEAD_ZONE ? 0 : x;
            state.joystickPosition.y = Math.abs(y) < CONFIG.DEAD_ZONE ? 0 : y;
        }

        function resetJoystick() {
            stick.style.transform = 'translate(0, 0)';
            state.joystickPosition = { x: 0, y: 0 };
            sendStop();
        }

        function startJoystickUpdates() {
            if (joystickInterval) return;

            joystickInterval = setInterval(() => {
                if (state.joystickActive) {
                    sendJoystickCommand(
                        state.joystickPosition.x,
                        state.joystickPosition.y
                    );
                }
            }, CONFIG.JOYSTICK_UPDATE_RATE);
        }

        function stopJoystickUpdates() {
            if (joystickInterval) {
                clearInterval(joystickInterval);
                joystickInterval = null;
            }
        }

        // Touch events
        zone.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            startTouch = touch.identifier;
            state.joystickActive = true;
            updateJoystickPosition(touch.clientX, touch.clientY);
            startJoystickUpdates();
            triggerHaptic();
        }, { passive: false });

        zone.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (!state.joystickActive) return;

            for (const touch of e.touches) {
                if (touch.identifier === startTouch) {
                    updateJoystickPosition(touch.clientX, touch.clientY);
                    break;
                }
            }
        }, { passive: false });

        zone.addEventListener('touchend', (e) => {
            e.preventDefault();
            // Only reset if the tracked touch ended
            const touchEnded = Array.from(e.changedTouches).some(
                t => t.identifier === startTouch
            );
            if (touchEnded) {
                state.joystickActive = false;
                stopJoystickUpdates();
                resetJoystick();
            }
        }, { passive: false });

        zone.addEventListener('touchcancel', (e) => {
            e.preventDefault();
            // Only reset if the tracked touch was canceled
            const touchCanceled = Array.from(e.changedTouches).some(
                t => t.identifier === startTouch
            );
            if (touchCanceled) {
                state.joystickActive = false;
                stopJoystickUpdates();
                resetJoystick();
            }
        }, { passive: false });

        // Mouse events for desktop
        let mouseDown = false;

        zone.addEventListener('mousedown', (e) => {
            mouseDown = true;
            state.joystickActive = true;
            updateJoystickPosition(e.clientX, e.clientY);
            startJoystickUpdates();
        });

        document.addEventListener('mousemove', (e) => {
            if (mouseDown && state.joystickActive) {
                updateJoystickPosition(e.clientX, e.clientY);
            }
        });

        document.addEventListener('mouseup', (e) => {
            if (mouseDown) {
                mouseDown = false;
                state.joystickActive = false;
                stopJoystickUpdates();
                resetJoystick();
            }
        });
    }

    // =========================================================================
    // Mode Switching
    // =========================================================================
    function setupModeSwitcher() {
        elements.modeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                switchMode(mode);
            });
        });
    }

    function switchMode(mode) {
        state.currentMode = mode;

        // Update button states
        elements.modeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Show/hide control panels
        elements.buttonControls.classList.toggle('active', mode === 'buttons');
        elements.joystickControls.classList.toggle('active', mode === 'joystick');

        // Stop motors when switching modes
        sendStop();
    }

    // =========================================================================
    // Speed Control
    // =========================================================================
    function setupSpeedControl() {
        elements.speedSlider.addEventListener('input', (e) => {
            const speed = e.target.value / 100;
            elements.speedLabel.textContent = `${e.target.value}%`;

            if (state.connected) {
                state.socket.emit('set_speed', { speed });
            }
        });
    }

    // =========================================================================
    // Action Buttons
    // =========================================================================
    function setupActionButtons() {
        // Helper to prevent double-fire on touch devices
        // Uses a WeakMap to track last touch time per element
        const lastTouchTime = new WeakMap();
        const TOUCH_CLICK_THRESHOLD = 500; // ms

        function addTouchClickHandler(element, handler) {
            element.addEventListener('touchstart', (e) => {
                e.preventDefault();
                lastTouchTime.set(element, Date.now());
                handler();
            }, { passive: false });

            element.addEventListener('click', () => {
                // Skip click if it follows a recent touch
                const lastTouch = lastTouchTime.get(element) || 0;
                if (Date.now() - lastTouch > TOUCH_CLICK_THRESHOLD) {
                    handler();
                }
            });
        }

        // Stop button
        addTouchClickHandler(elements.btnStop, () => {
            sendStop();
            triggerHaptic();
        });

        // Emergency stop button
        addTouchClickHandler(elements.btnEmergency, () => {
            sendEmergencyStop();
        });

        // Reset emergency button
        elements.resetEmergency.addEventListener('click', () => {
            sendEmergencyReset();
        });

        // Photo button
        elements.btnPhoto.addEventListener('click', () => {
            if (state.connected) {
                state.socket.emit('take_photo');
                triggerHaptic();
            }
        });
    }

    // =========================================================================
    // Takeover Modal
    // =========================================================================
    function setupTakeoverModal() {
        elements.approveTakeover.addEventListener('click', () => {
            if (state.connected) {
                state.socket.emit('approve_takeover');
            }
            elements.takeoverModal.classList.add('hidden');
        });

        elements.denyTakeover.addEventListener('click', () => {
            if (state.connected) {
                state.socket.emit('deny_takeover');
            }
            elements.takeoverModal.classList.add('hidden');
        });
    }

    // =========================================================================
    // Fullscreen
    // =========================================================================
    function setupFullscreen() {
        elements.fullscreenToggle.addEventListener('click', () => {
            toggleFullscreen();
        });

        // Sync CSS class when fullscreen state changes (e.g., via Escape key)
        document.addEventListener('fullscreenchange', () => {
            const container = elements.cameraContainer;
            if (!document.fullscreenElement) {
                container.classList.remove('fullscreen');
            }
        });
    }

    function toggleFullscreen() {
        const container = elements.cameraContainer;

        if (container.classList.contains('fullscreen')) {
            container.classList.remove('fullscreen');
            if (document.exitFullscreen) {
                document.exitFullscreen().catch(() => {});
            }
        } else {
            container.classList.add('fullscreen');
            if (container.requestFullscreen) {
                container.requestFullscreen().catch(() => {});
            }
        }
    }

    // =========================================================================
    // Haptic Feedback
    // =========================================================================
    function triggerHaptic(duration = CONFIG.HAPTIC_DURATION) {
        if ('vibrate' in navigator) {
            navigator.vibrate(duration);
        }
    }

    // =========================================================================
    // Prevent Default Touch Behaviors
    // =========================================================================
    function setupTouchPrevention() {
        // Prevent pull-to-refresh
        document.body.addEventListener('touchmove', (e) => {
            if (e.target.closest('#control-panel')) {
                // Allow scrolling in control panel if needed
                return;
            }
            e.preventDefault();
        }, { passive: false });

        // Prevent double-tap zoom on buttons
        document.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('touchend', (e) => {
                e.preventDefault();
            }, { passive: false });
        });

        // Prevent context menu on long press
        document.addEventListener('contextmenu', (e) => {
            if (e.target.closest('#control-panel') || e.target.closest('#camera-container')) {
                e.preventDefault();
            }
        });
    }

    // =========================================================================
    // Orientation Lock (if supported)
    // =========================================================================
    function setupOrientationLock() {
        if (screen.orientation && screen.orientation.lock) {
            // Try to lock to portrait, but don't fail if not supported
            screen.orientation.lock('portrait').catch(() => {
                // Orientation lock not supported or denied
            });
        }
    }

    // =========================================================================
    // Keyboard Controls (Desktop)
    // =========================================================================
    function setupKeyboardControls() {
        const keyMap = {
            'w': { left: 1, right: 1 },      // Forward
            's': { left: -1, right: -1 },    // Reverse
            'a': { left: 0, right: 1 },      // Turn left
            'd': { left: 1, right: 0 },      // Turn right
            'q': { left: -1, right: 1 },     // Spin left
            'e': { left: 1, right: -1 },     // Spin right
            'ArrowUp': { left: 1, right: 1 },
            'ArrowDown': { left: -1, right: -1 },
            'ArrowLeft': { left: 0, right: 1 },
            'ArrowRight': { left: 1, right: 0 },
        };

        const activeKeys = new Set();

        document.addEventListener('keydown', (e) => {
            // Ignore if typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Space bar = emergency stop
            if (e.code === 'Space') {
                e.preventDefault();
                sendEmergencyStop();
                return;
            }

            // Escape = normal stop
            if (e.code === 'Escape') {
                e.preventDefault();
                sendStop();
                return;
            }

            const mapping = keyMap[e.key];
            if (mapping && !activeKeys.has(e.key)) {
                e.preventDefault();
                activeKeys.add(e.key);
                sendDriveCommand(mapping.left, mapping.right);
            }
        });

        document.addEventListener('keyup', (e) => {
            if (keyMap[e.key]) {
                e.preventDefault();
                activeKeys.delete(e.key);

                // Only stop if no keys are pressed
                if (activeKeys.size === 0) {
                    sendStop();
                }
            }
        });
    }

    // =========================================================================
    // Initialization
    // =========================================================================
    function init() {
        // Cache DOM elements
        cacheElements();

        // Setup all components
        setupButtonControls();
        setupJoystick();
        setupModeSwitcher();
        setupSpeedControl();
        setupActionButtons();
        setupTakeoverModal();
        setupFullscreen();
        setupTouchPrevention();
        setupKeyboardControls();

        // Try to lock orientation
        setupOrientationLock();

        // Connect to server
        connectSocket();

        console.log('MonsterBorg Web Interface initialized');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
