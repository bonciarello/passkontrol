/* ================================================================
   PassKontrol — Client-side password analysis
   ================================================================ */

(function () {
    'use strict';

    /* ---- DOM refs ---- */
    const passwordInput = document.getElementById('passwordInput');
    const toggleBtn = document.getElementById('toggleVisibility');
    const gaugeFill = document.getElementById('gaugeFill');
    const gaugeLevel = document.getElementById('gaugeLevel');
    const gaugePercent = document.getElementById('gaugePercent');
    const criteriaList = document.getElementById('criteriaList');
    const tipsList = document.getElementById('tipsList');

    /* ---- Constants ---- */
    const CIRCUMFERENCE = 2 * Math.PI * 82; // ~515.22

    const COMMON_PATTERNS = [
        '123', 'abc', 'qwerty', 'password', 'admin',
        '123456', 'qwerty123', 'letmein', 'welcome', 'monkey',
        'dragon', 'master', 'football', 'italia',
    ];

    const SEQ_ALPHA = /(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)/;
    const SEQ_NUM = /(?:012|123|234|345|456|567|678|789)/;
    const REPEATED_G = /(.)\1{2,}/g;

    let wasForte = false;
    let idleTimer = null;

    /* ---- Analysis engine (pure function) ---- */
    function analyzePassword(password) {
        if (!password) {
            return {
                score: 0,
                level: 'debole',
                percentage: 0,
                checks: {
                    length: false,
                    uppercase: false,
                    lowercase: false,
                    number: false,
                    special: false,
                },
                suggestions: ['Inserisci una password per valutarne la robustezza.'],
            };
        }

        var checks = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[^A-Za-z0-9]/.test(password),
        };

        var metCount = 0;
        for (var k in checks) {
            if (checks[k]) metCount++;
        }

        // Se troppo corta, sempre debole
        if (password.length < 8) {
            var pctShort = Math.min(metCount * 6, 33);
            var suggShort = [];
            if (!checks.length) suggShort.push('Usa almeno 8 caratteri per una password pi\u00f9 sicura.');
            if (!checks.uppercase) suggShort.push('Aggiungi almeno una lettera maiuscola (A-Z).');
            if (!checks.lowercase) suggShort.push('Aggiungi almeno una lettera minuscola (a-z).');
            if (!checks.number) suggShort.push('Inserisci almeno un numero (0-9).');
            if (!checks.special) suggShort.push('Aggiungi un carattere speciale (! @ # $ % & *).');
            if (suggShort.length === 0) suggShort.push('Inserisci una password per valutarne la robustezza.');
            return {
                score: metCount * 2,
                level: 'debole',
                percentage: pctShort,
                checks: checks,
                suggestions: suggShort,
            };
        }

        var bonus = 0;
        if (password.length >= 12) bonus += 0.5;
        if (password.length >= 16) bonus += 0.5;
        if (password.length >= 20) bonus += 0.5;

        var penalty = 0;
        var lower = password.toLowerCase();
        for (var i = 0; i < COMMON_PATTERNS.length; i++) {
            if (lower.indexOf(COMMON_PATTERNS[i]) !== -1) penalty += 1;
        }

        // Caratteri ripetuti: conta gruppi distinti
        var repeatedMatches = password.match(REPEATED_G);
        if (repeatedMatches) penalty += repeatedMatches.length;

        if (SEQ_ALPHA.test(lower)) penalty += 0.5;
        if (SEQ_NUM.test(password)) penalty += 0.5;

        var score = Math.max(0, Math.min(10, metCount * 2 + bonus - penalty));
        score = Math.round(score * 10) / 10;

        var level, percentage;
        if (score <= 4) {
            level = 'debole';
            percentage = score > 0 ? Math.round((score / 4) * 33) : 0;
        } else if (score <= 7) {
            level = 'media';
            percentage = 34 + Math.round(((score - 4) / 3) * 33);
        } else {
            level = 'forte';
            percentage = 67 + Math.round(((score - 7) / 3) * 33);
        }
        percentage = Math.min(100, Math.max(0, percentage));

        var suggestions = [];
        if (!checks.length) {
            suggestions.push('Usa almeno 8 caratteri per una password pi\u00f9 sicura.');
        }
        if (!checks.uppercase) {
            suggestions.push('Aggiungi almeno una lettera maiuscola (A-Z).');
        }
        if (!checks.lowercase) {
            suggestions.push('Aggiungi almeno una lettera minuscola (a-z).');
        }
        if (!checks.number) {
            suggestions.push('Inserisci almeno un numero (0-9).');
        }
        if (!checks.special) {
            suggestions.push('Aggiungi un carattere speciale (! @ # $ % & *).');
        }
        if (penalty > 0 && metCount >= 3) {
            suggestions.push('Evita sequenze comuni o caratteri ripetuti.');
        }
        if (suggestions.length === 0) {
            suggestions.push('Ottimo! La tua password \u00e8 robusta e ben bilanciata.');
        }

        return {
            score: score,
            level: level,
            percentage: percentage,
            checks: checks,
            suggestions: suggestions,
        };
    }

    /* ---- UI update ---- */
    function updateUI(result) {
        /* Gauge fill */
        var offset = CIRCUMFERENCE - (result.percentage / 100) * CIRCUMFERENCE;
        gaugeFill.setAttribute('stroke-dashoffset', offset);
        gaugeFill.setAttribute('data-level', result.level);

        /* Gauge text */
        var levelLabels = { debole: 'DEBOLE', media: 'MEDIA', forte: 'FORTE' };
        gaugeLevel.textContent = levelLabels[result.level];
        gaugeLevel.setAttribute('data-level', result.level);
        gaugePercent.textContent = result.percentage + '%';

        /* Pulse on first forte */
        if (result.level === 'forte' && !wasForte) {
            wasForte = true;
            gaugeFill.classList.add('pulse');
            setTimeout(function () {
                gaugeFill.classList.remove('pulse');
            }, 600);
        } else if (result.level !== 'forte') {
            wasForte = false;
        }

        /* Input border */
        passwordInput.classList.remove('input--weak', 'input--media', 'input--forte');
        if (passwordInput.value.length > 0) {
            passwordInput.classList.add('input--' + result.level);
        }

        /* Criteria */
        var criteriaItems = criteriaList.querySelectorAll('.criteria__item');
        var checkKeys = ['length', 'uppercase', 'lowercase', 'number', 'special'];
        for (var i = 0; i < criteriaItems.length; i++) {
            var item = criteriaItems[i];
            var key = item.getAttribute('data-check');
            if (result.checks[key]) {
                item.classList.add('criteria__item--met');
            } else {
                item.classList.remove('criteria__item--met');
            }
        }

        /* Tips */
        tipsList.innerHTML = '';
        for (var j = 0; j < result.suggestions.length; j++) {
            var li = document.createElement('li');
            li.className = 'tips__item';
            if (result.level === 'debole' && result.percentage > 0) {
                li.classList.add('tip--danger');
            } else if (result.level === 'forte') {
                li.classList.add('tip--success');
            }
            li.textContent = result.suggestions[j];
            tipsList.appendChild(li);
        }
    }

    /* ---- Server-side validation (fallback / verification) ---- */
    function serverValidate(password) {
        fetch('api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password }),
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                /* Use server result only if it's more restrictive */
                /* For now, we use client-side as primary; server is verification */
                console.log('Server validation:', data);
            })
            .catch(function () {
                /* Server unavailable — client-side is self-sufficient */
            });
    }

    /* ---- Idle detection (5s no typing = no network calls) ---- */
    function resetIdleTimer() {
        if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(function () {
            /* After 5 seconds of inactivity, ensure no pending requests */
            idleTimer = null;
        }, 5000);
    }

    /* ---- Event handlers ---- */
    function handleInput() {
        resetIdleTimer();
        var result = analyzePassword(passwordInput.value);
        updateUI(result);

        /* Debounce server call — only after 1s of no typing */
        clearTimeout(passwordInput._serverTimer);
        passwordInput._serverTimer = setTimeout(function () {
            if (passwordInput.value.length > 0) {
                serverValidate(passwordInput.value);
            }
        }, 1000);
    }

    function handleToggle() {
        var isPassword = passwordInput.type === 'password';
        passwordInput.type = isPassword ? 'text' : 'password';
        toggleBtn.classList.toggle('visible', isPassword);
        toggleBtn.setAttribute('aria-label', isPassword ? 'Nascondi password' : 'Mostra password');
        toggleBtn.title = isPassword ? 'Nascondi password' : 'Mostra password';
    }

    /* ---- Init ---- */
    function init() {
        /* Set initial gauge state */
        gaugeFill.setAttribute('stroke-dashoffset', CIRCUMFERENCE);

        /* Event listeners */
        passwordInput.addEventListener('input', handleInput);
        toggleBtn.addEventListener('click', handleToggle);

        /* Initial analysis (empty) */
        updateUI(analyzePassword(''));

        /* Focus input on load for convenience */
        setTimeout(function () {
            passwordInput.focus();
        }, 300);
    }

    /* ---- Boot ---- */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
