/**
 * DexIQ Audience Q&A — Question submission form logic.
 *
 * Handles the audience-facing Q&A page where people submit questions
 * via their phones after scanning the QR code.
 */

(function () {
    'use strict';

    const form = document.getElementById('question-form');
    const nameInput = document.getElementById('name');
    const questionInput = document.getElementById('question');
    const submitBtn = document.getElementById('submit-btn');
    const charCount = document.getElementById('char-count');
    const successMessage = document.getElementById('success-message');
    const errorMessage = document.getElementById('error-message');

    // Character counter
    questionInput.addEventListener('input', function () {
        charCount.textContent = questionInput.value.length;
    });

    // Form submission
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const name = nameInput.value.trim();
        const question = questionInput.value.trim();

        if (!question) {
            showError('Please enter a question.');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
        hideError();

        try {
            const response = await fetch('/api/questions/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name || null,
                    question: question,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Submission failed.');
            }

            // Success
            form.style.display = 'none';
            successMessage.style.display = 'block';

        } catch (err) {
            showError(err.message || 'Something went wrong. Please try again.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Question';
        }
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorMessage.style.display = 'block';
    }

    function hideError() {
        errorMessage.style.display = 'none';
    }

})();
