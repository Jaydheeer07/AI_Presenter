/**
 * DexIQ AI Avatar — Audio-reactive visualization module.
 *
 * Provides the pulsating avatar effect that responds to audio playback.
 * Used by presenter.js to create the illusion of the AI "speaking."
 */

(function () {
    'use strict';

    // Avatar state management (exported for presenter.js)
    window.DexIQAvatar = {
        currentMode: 'idle',

        /**
         * Set the avatar visual mode.
         * @param {string} mode - One of: idle, speaking, speaking_live, thinking, listening
         */
        setMode: function (mode) {
            this.currentMode = mode;
            const avatar = document.getElementById('avatar');
            if (!avatar) return;

            avatar.className = 'avatar avatar-' + mode.replace('_', '-');
        },

        /**
         * Get the current avatar mode.
         * @returns {string}
         */
        getMode: function () {
            return this.currentMode;
        },
    };

})();
